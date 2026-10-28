"""Runs a script on a worker thread and relays its output, prompts and `update()` calls to the GUI thread.

The worker calls `scripting.run_script` with a `_QtHost`: `print` / `clear` / `message` / `progress` are
forwarded as signals; `input_text` / `confirm` / `update` emit a request and block the worker until the GUI
answers with `reply()`. `stop()` sets the stop event (the script's trace function raises at the next line)
and releases any pending wait, so the Stop button works inside loops, prompts and sleeps alike.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Signal

from ..fractal.scene import Flame
from ..scripting.api import ScriptHost, ScriptStopped
from ..scripting.runner import ScriptResult, run_script

REQUEST_INPUT, REQUEST_CONFIRM, REQUEST_UPDATE = "input", "confirm", "update"


class _QtHost(ScriptHost):
    """The worker-side host: signals out, a condition variable for answers coming back."""

    def __init__(self, runner: "ScriptRunner", stop_event: threading.Event):
        self._runner = runner
        self._stop = stop_event
        self._answer = threading.Event()
        self._value = None

    def print(self, text: str) -> None:
        self._runner.output.emit(text)

    def clear(self) -> None:
        self._runner.cleared.emit()

    def message(self, text: str) -> None:
        self._runner.message.emit(text)

    def progress(self, fraction: float) -> None:
        self._runner.progress.emit(fraction)

    def input_text(self, prompt: str, default: str) -> str | None:
        return self._ask(REQUEST_INPUT, prompt, default)

    def confirm(self, text: str) -> bool:
        return bool(self._ask(REQUEST_CONFIRM, text, ""))

    def update(self, flame: Flame, wait: bool) -> None:
        self._answer.clear()
        self._runner.update_requested.emit(flame, wait)
        self._wait()

    def _ask(self, kind: str, prompt: str, default: str):
        self._answer.clear()
        self._runner.input_requested.emit(kind, prompt, default)
        return self._wait()

    def _wait(self):
        while not self._answer.wait(0.05):
            if self._stop.is_set():
                raise ScriptStopped("stopped by the user")
        if self._stop.is_set():
            raise ScriptStopped("stopped by the user")
        return self._value

    def answer(self, value) -> None:
        self._value = value
        self._answer.set()


class ScriptRunner(QObject):
    """Runs one script at a time on a thread.

    Signals:
        output(str): Text from `print` (includes the newline).
        cleared(): The script cleared the output.
        message(str): `message()` — show a message box.
        progress(float): `progress()` 0..1.
        input_requested(str, str, str): (kind, prompt, default) — answer with `reply()`.
        update_requested(object, bool): (flame, wait) — apply it, then `reply()`.
        finished(object): The ScriptResult.
    """
    output = Signal(str)
    cleared = Signal()
    message = Signal(str)
    progress = Signal(float)
    input_requested = Signal(str, str, str)
    update_requested = Signal(object, bool)
    finished = Signal(object)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._host: _QtHost | None = None
        self._result: ScriptResult | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def run(self, code: str, flame: Flame | None, active: int = 0) -> None:
        """Start `code` against a copy of `flame`; `finished` reports the outcome."""
        if self.running:
            raise RuntimeError("a script is already running")
        self._stop = threading.Event()
        self._host = _QtHost(self, self._stop)
        host, stop = self._host, self._stop
        snapshot = flame.copy() if flame is not None else None

        def work() -> None:
            result = run_script(code, snapshot, host, stop, active)
            self.finished.emit(result)

        self._thread = threading.Thread(target=work, name="fractalchemy-script", daemon=True)
        self._thread.start()

    def reply(self, value=None) -> None:
        """Answer the pending input / confirm / update request."""
        if self._host is not None:
            self._host.answer(value)

    def stop(self) -> None:
        """Ask the running script to stop (it ends at its next line, or immediately if it is waiting)."""
        self._stop.set()

    def wait(self, timeout: float | None = None) -> bool:
        """Block until the thread ends (tests); True if it did."""
        if self._thread is None:
            return True
        self._thread.join(timeout)
        return not self._thread.is_alive()


__all__ = ["ScriptRunner", "REQUEST_INPUT", "REQUEST_CONFIRM", "REQUEST_UPDATE"]
