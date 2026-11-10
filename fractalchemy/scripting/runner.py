"""Runs a script: compile, execute against a `ScriptContext`, and report the outcome with a line number.

`run_script` is synchronous and Qt-free; the Script Editor calls it on a worker thread with a host whose
prompts block until the GUI answers. Stopping works through a trace function installed on that thread:
every new line the script executes checks the stop event and raises `ScriptStopped` when it is set, so even
`while True:` loops end promptly. Waits inside the API (`sleep`, prompts, `update`) poll the same event.
"""

from __future__ import annotations

import math
import sys
import threading
import time
import traceback
from dataclasses import dataclass, field

from ..fractal.scene import Flame
from .api import LiveRefused, ScriptContext, ScriptHost, ScriptStopped
from .parameters import ParamSpec

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
        declarations: The `param()` declarations, in the order the script made them.
        values: The value each parameter had in this run.
        effects: The kinds of side effect the script made (`prompt`, `message`, `update`, `sleep`, `write`, `read`).
        refused: When a restricted run was stopped before a side effect, why (the effect did not happen).
        seed: The seed the script's random numbers used (None: unseeded).
        variables: The plain-data variables the script defined (numbers, strings, and tuples / lists / dicts of them) —
            what the Script Editor's console carries from one line to the next.
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
    declarations: tuple[ParamSpec, ...] = ()
    values: dict = field(default_factory=dict)
    effects: frozenset = frozenset()
    refused: str = ""
    seed: int | None = None
    variables: dict = field(default_factory=dict)


def is_plain(value, depth: int = 0) -> bool:
    """Plain data that `repr` writes back as Python: numbers, strings, booleans, None, and tuples / lists / dicts of them."""
    if depth > 4 or isinstance(value, float) and not math.isfinite(value):
        return False
    if value is None or isinstance(value, (bool, int, float, str)):
        return True
    if isinstance(value, (tuple, list)):
        return len(value) <= 1000 and all(is_plain(v, depth + 1) for v in value)
    if isinstance(value, dict):
        return len(value) <= 1000 and all(is_plain(k, depth + 1) and is_plain(v, depth + 1) for k, v in value.items())
    return False


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
               active: int = 0, seed: int | None = None, parameters: dict | None = None, restricted: str | None = None) -> ScriptResult:
    """Execute `code` against a copy of `flame` and return what happened.

    Args:
        code: The script source.
        flame: The flame to edit (copied; the caller applies `result.flame` if it wants the changes).
        host: Output / prompts / update callbacks (a silent default if None).
        stop_event: Set it from another thread to stop the script.
        active: Index of the active transform when the script starts.
        seed: Seed for the script's random numbers (None = random).
        parameters: Values for the script's `param()` declarations, by name.
        restricted: Refuse side effects, saying when ("while its controls update live"); see `api.LiveRefused`.
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
    context = ScriptContext(flame, host, active, seed, parameters, restricted)
    namespace = context.namespace()
    given = set(namespace)

    def done(ok: bool, **fields) -> ScriptResult:
        return ScriptResult(ok, flame=context.flame, active=context.active, seconds=time.monotonic() - started,
                            output_lines=context.output_lines, declarations=tuple(context.declarations.values()),
                            values=dict(context.values), effects=frozenset(context.effects), seed=seed,
                            variables={k: v for k, v in namespace.items() if k not in given and not k.startswith("_") and is_plain(v)},
                            **fields)

    compiled = compile(code, SCRIPT_FILENAME, "exec")
    previous = sys.gettrace()
    sys.settrace(_StopTrace(stop_event))
    try:
        exec(compiled, namespace)   # noqa: S102 - running the user's script is the point
    except LiveRefused as refused:
        return done(True, stopped=True, stop_reason=refused.reason, refused=f"{refused.reason} (line {_script_line(refused)})"
                    if _script_line(refused) else refused.reason)
    except ScriptStopped as stopped:
        return done(True, stopped=True, stop_reason=stopped.reason, user_stopped=stop_event.is_set())
    except SystemExit as exc:   # exit() / quit() in a script: treat like stop()
        return done(True, stopped=True, stop_reason=str(exc.code) if exc.code not in (None, 0) else "")
    except RecursionError as exc:
        return done(False, error=ScriptErrorInfo("RecursionError", "maximum recursion depth exceeded", _script_line(exc)))
    except Exception as exc:  # noqa: BLE001 - whatever the script raised is reported, not propagated
        kind = type(exc).__name__
        message = str(exc)
        if isinstance(exc, KeyError) and exc.args:
            message = f"no such key: {exc.args[0]!r}"
        return done(False, error=ScriptErrorInfo(kind, message, _script_line(exc), None, _script_traceback(exc)))
    except BaseException as exc:  # noqa: BLE001 - KeyboardInterrupt and friends must still end in a result
        return done(False, error=ScriptErrorInfo(type(exc).__name__, str(exc) or type(exc).__name__, _script_line(exc)))
    finally:
        sys.settrace(previous)
    return done(True)


__all__ = ["ScriptResult", "ScriptErrorInfo", "run_script", "check_syntax", "SCRIPT_FILENAME"]
