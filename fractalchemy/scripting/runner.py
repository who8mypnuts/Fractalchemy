"""Runs a script: compile, execute against a `ScriptContext`, and report the outcome with a line number.

`run_script` is synchronous and Qt-free; the Script Editor calls it on a worker thread with a host whose
prompts block until the GUI answers. Stopping works through a trace function installed on that thread:
every new line the script executes checks the stop event and raises `ScriptStopped` when it is set, so even
`while True:` loops end promptly. Waits inside the API (`sleep`, prompts, `update`) poll the same event.
"""

from __future__ import annotations

import sys
import threading
import time
import traceback
from dataclasses import dataclass, field

from ..fractal.scene import Flame
from .api import ScriptContext, ScriptHost, ScriptStopped

SCRIPT_FILENAME = "<script>"


@dataclass
class ScriptErrorInfo:
    """Where and why a script failed.

    Attributes:
        kind: The exception class name (`SyntaxError`, `ScriptError`, `ZeroDivisionError`, …).
        message: Its text.
        line: The script line (1-based) where it happened, if known.
        column: Column within that line, if known (syntax errors).
        details: The traceback restricted to script frames (for the output panel).
    """
    kind: str
    message: str
    line: int | None = None
    column: int | None = None
    details: str = ""

    def __str__(self) -> str:
        where = f" (line {self.line}" + (f", col {self.column}" if self.column else "") + ")" if self.line else ""
        return f"{self.kind}: {self.message}{where}"


@dataclass
class ScriptResult:
    """What happened when a script ran.

    Attributes:
        ok: It finished (or stopped itself with `stop()`) without an error.
        stopped: It ended through `stop()` or the Stop button.
        stop_reason: The text given to `stop()`.
        error: The failure, when `ok` is False.
        flame: The flame after the script (only meaningful when `ok`).
        active: The active transform index after the script.
        seconds: Wall time.
        output_lines: How many `print` calls were made.
    """
    ok: bool
    stopped: bool = False
    stop_reason: str = ""
    error: ScriptErrorInfo | None = None
    flame: Flame | None = None
    active: int = 0
    seconds: float = 0.0
    output_lines: int = 0
    user_stopped: bool = False
    flame_changed: bool = field(default=True)


def check_syntax(code: str) -> ScriptErrorInfo | None:
    """Compile only; the SyntaxError (with line and column) if there is one."""
    try:
        compile(code, SCRIPT_FILENAME, "exec")
    except SyntaxError as exc:
        return ScriptErrorInfo("SyntaxError", exc.msg or str(exc), exc.lineno, exc.offset)
    except ValueError as exc:   # e.g. null bytes
        return ScriptErrorInfo("ValueError", str(exc))
    return None


def _script_line(exc: BaseException) -> int | None:
    """The innermost script line in the exception's traceback."""
    line = None
    for frame in traceback.extract_tb(exc.__traceback__):
        if frame.filename == SCRIPT_FILENAME:
            line = frame.lineno
    return line


def _script_traceback(exc: BaseException) -> str:
    frames = [f for f in traceback.extract_tb(exc.__traceback__) if f.filename == SCRIPT_FILENAME]
    lines = traceback.format_list(frames) if frames else []
    return "".join(lines).rstrip()


class _StopTrace:
    """The trace function: raises ScriptStopped once the event is set (checked on every new line)."""

    def __init__(self, stop_event: threading.Event):
        self._stop = stop_event

    def __call__(self, frame, event, arg):
        if self._stop.is_set():
            raise ScriptStopped("stopped by the user")
        if event == "call" and frame.f_code.co_filename != SCRIPT_FILENAME:
            return None   # don't slow down library code: only script frames are traced line by line
        return self


def run_script(code: str, flame: Flame | None, host: ScriptHost | None = None, stop_event: threading.Event | None = None,
               active: int = 0, seed: int | None = None) -> ScriptResult:
    """Execute `code` against a copy of `flame` and return what happened.

    Args:
        code: The script source.
        flame: The flame to edit (copied; the caller applies `result.flame` if it wants the changes).
        host: Output / prompts / update callbacks (a silent default if None).
        stop_event: Set it from another thread to stop the script.
        active: Index of the active transform when the script starts.
        seed: Seed for the script's random numbers (None = random).
    """
    stop_event = stop_event or threading.Event()
    host = host or ScriptHost()

    def check_stop() -> None:
        if stop_event.is_set():
            raise ScriptStopped("stopped by the user")

    host.check_stop = check_stop   # waits inside the API (sleep, prompts, update) poll the same event
    started = time.monotonic()
    syntax = check_syntax(code)
    if syntax is not None:
        return ScriptResult(False, error=syntax, flame=flame.copy() if flame else None, active=active)
    context = ScriptContext(flame, host, active, seed)
    namespace = context.namespace()
    compiled = compile(code, SCRIPT_FILENAME, "exec")
    previous = sys.gettrace()
    sys.settrace(_StopTrace(stop_event))
    try:
        exec(compiled, namespace)   # noqa: S102 - running the user's script is the point
    except ScriptStopped as stopped:
        return ScriptResult(True, stopped=True, stop_reason=stopped.reason, flame=context.flame, active=context.active,
                            seconds=time.monotonic() - started, output_lines=context.output_lines, user_stopped=stop_event.is_set())
    except SystemExit as exc:   # exit() / quit() in a script: treat like stop()
        return ScriptResult(True, stopped=True, stop_reason=str(exc.code) if exc.code not in (None, 0) else "", flame=context.flame,
                            active=context.active, seconds=time.monotonic() - started, output_lines=context.output_lines)
    except RecursionError as exc:
        return ScriptResult(False, error=ScriptErrorInfo("RecursionError", "maximum recursion depth exceeded", _script_line(exc)),
                            flame=context.flame, active=context.active, seconds=time.monotonic() - started, output_lines=context.output_lines)
    except Exception as exc:  # noqa: BLE001 - whatever the script raised is reported, not propagated
        kind = type(exc).__name__
        message = str(exc)
        if isinstance(exc, KeyError) and exc.args:
            message = f"no such key: {exc.args[0]!r}"
        return ScriptResult(False, error=ScriptErrorInfo(kind, message, _script_line(exc), None, _script_traceback(exc)),
                            flame=context.flame, active=context.active, seconds=time.monotonic() - started, output_lines=context.output_lines)
    except BaseException as exc:  # noqa: BLE001 - KeyboardInterrupt and friends must still end in a result
        return ScriptResult(False, error=ScriptErrorInfo(type(exc).__name__, str(exc) or type(exc).__name__, _script_line(exc)),
                            flame=context.flame, active=context.active, seconds=time.monotonic() - started, output_lines=context.output_lines)
    finally:
        sys.settrace(previous)
    return ScriptResult(True, flame=context.flame, active=context.active, seconds=time.monotonic() - started,
                        output_lines=context.output_lines)


__all__ = ["ScriptResult", "ScriptErrorInfo", "run_script", "check_syntax", "SCRIPT_FILENAME"]
