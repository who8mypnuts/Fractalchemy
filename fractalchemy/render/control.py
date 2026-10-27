"""Cancel / pause control shared by the final renderer, its Qt job and the samplers.

The GUI thread flips the flags; the render thread (and, through mirrored flags, the CPU worker
processes) checks them between chunks of work. Time spent paused is tracked so the clock shown
to the user keeps meaning "time the render actually ran".
"""

from __future__ import annotations

import threading
import time


class RenderControl:
    """Cancel / pause flags shared between the GUI and the render thread; tracks time spent paused."""

    def __init__(self):
        self._cancel = threading.Event()
        self._resume = threading.Event()
        self._resume.set()
        self._paused_since: float | None = None
        self.paused_seconds = 0.0
        self._lock = threading.Lock()

    def cancel(self) -> None:
        """Stop as soon as possible (also releases a pause)."""
        self._cancel.set()
        self._resume.set()

    def pause(self) -> None:
        """Hold the render between chunks until `resume`."""
        with self._lock:
            if self._resume.is_set():
                self._resume.clear()
                self._paused_since = time.perf_counter()

    def resume(self) -> None:
        """Continue after `pause`."""
        with self._lock:
            if not self._resume.is_set():
                self.paused_seconds += time.perf_counter() - (self._paused_since or time.perf_counter())
                self._paused_since = None
                self._resume.set()

    @property
    def paused(self) -> bool:
        """True while paused."""
        return not self._resume.is_set()

    def cancelled(self) -> bool:
        """True once `cancel` was called."""
        return self._cancel.is_set()

    def wait_if_paused(self) -> bool:
        """Block while paused; returns False if cancelled (so callers can bail out)."""
        self._resume.wait()
        return not self._cancel.is_set()


__all__ = ["RenderControl"]
