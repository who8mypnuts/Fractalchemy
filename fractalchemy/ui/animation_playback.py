"""Playback of an `AnimationDocument`: the playhead advances in wall-clock time at the animation's frame rate.

The preview renders whatever frame the playhead is on when it is free, so frames are *dropped*
rather than delayed when the engine is slower than real time — timing stays true. A playback
*session* lasts from Play until Stop: a pause keeps it, so Stop still returns to where playback
started.
"""

from __future__ import annotations

import time

from PySide6.QtCore import QObject, QTimer, Signal

from .animation_document import AnimationDocument

TICK_MS = 15


class Playback(QObject):
    """Drives the document's playhead (see the module docstring).

    Signals:
        state_changed(): Playing started / paused / stopped (the window refreshes its buttons).
    """
    state_changed = Signal()

    def __init__(self, document: AnimationDocument, parent: QObject | None = None):
        super().__init__(parent)
        self.document = document
        self._timer = QTimer(self, interval=TICK_MS)
        self._timer.timeout.connect(self._tick)
        self._started = 0.0
        self._from = 0
        self._session = False

    @property
    def playing(self) -> bool:
        """True while the playhead advances."""
        return self._timer.isActive()

    @property
    def in_session(self) -> bool:
        """True from Play until Stop (paused included)."""
        return self._session

    def play(self) -> bool:
        """Start (or resume) from the playhead — from the start when it sits at the end; False without keyframes."""
        anim = self.document.animation
        if not anim.keyframes:
            self.state_changed.emit()
            return False
        if self.document.frame >= anim.last_frame and not anim.loop:
            self.document.set_frame(0)
        if not self._session:
            self._from = self.document.frame
            self._session = True
        self._started = time.monotonic() - (self.document.frame - self._from) / max(1, anim.fps)
        self._timer.start()
        self.state_changed.emit()
        return True

    def pause(self) -> None:
        """Hold the playhead where it is."""
        self._timer.stop()
        self.state_changed.emit()

    def toggle(self) -> None:
        """Play, or pause when playing."""
        if self.playing:
            self.pause()
        else:
            self.play()

    def stop(self, rewind: bool = True) -> None:
        """End the session; by default the playhead returns to where playback started."""
        self._timer.stop()
        if self._session and rewind:
            self.document.set_frame(self._from)
        self._session = False
        self.state_changed.emit()

    def _tick(self) -> None:
        anim = self.document.animation
        frame = self._from + int((time.monotonic() - self._started) * anim.fps)
        if frame >= anim.total_frames:
            if not anim.loop:
                self._timer.stop()
                self._session = False
                self.document.set_frame(anim.last_frame)
                self.state_changed.emit()
                return
            frame %= anim.total_frames
        self.document.set_frame(frame)


__all__ = ["Playback"]
