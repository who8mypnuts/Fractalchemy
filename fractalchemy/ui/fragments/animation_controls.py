"""The animation toolbar — FragM's *Rendering Mode* and *Time* toolbars with the wall clock behind them.

*Progressive* accumulates subframes of one still frame; *Animation* advances `time` at the frame rate while
playing (`F11` play, `F12` stop, `F10` rewind, Space in the viewport). The time slider runs over `length · fps`
frames (a page step is one second) with tick marks at the keyframes; the label reads `Time: 3s:12f`. The clock is
wall time: frame = frame at play + elapsed · fps, so a slow render drops frames rather than slowing the animation;
at the end playback stops (or starts again with *Loop play*). Nothing here knows the document — the window applies
the frame (camera path, easing curves, the `time` uniform).
"""

from __future__ import annotations

import time

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QButtonGroup, QLabel, QPushButton, QSlider, QSpinBox, QToolBar, QWidget

from ...fragments.animation import AnimationSettings
from ...widgets.actions import make_action
from ...widgets.silent import blocked

TICK_MS = 30
PROGRESSIVE, ANIMATION = "progressive", "animation"


class AnimationControls(QWidget):
    """Owns the two toolbars' widgets, the actions and the clock (see the module docstring).

    Signals:
        frame_changed(int): The current frame moved (playback, the slider, rewind).
        mode_changed(str): `progressive` / `animation`.
        playing_changed(bool): Playback started / stopped.
        settings_changed(object): The `AnimationSettings` (fps / length) were edited.
    """
    frame_changed = Signal(int)
    mode_changed = Signal(str)
    playing_changed = Signal(bool)
    settings_changed = Signal(object)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.settings = AnimationSettings()
        self.mode = PROGRESSIVE
        self.frame = 0
        self._playing = False
        self._play_started_frame = 0
        self._play_started_at = 0.0
        self._clock = QTimer(self, interval=TICK_MS)
        self._clock.timeout.connect(self._tick)
        self.progressive_button = QPushButton("Progressive", self)
        self.animation_button = QPushButton("Animation", self)
        for button in (self.progressive_button, self.animation_button):
            button.setCheckable(True)
        self.progressive_button.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self.progressive_button)
        group.addButton(self.animation_button)
        self.progressive_button.clicked.connect(lambda: self.set_mode(PROGRESSIVE))
        self.animation_button.clicked.connect(lambda: self.set_mode(ANIMATION))
        self.rewind_action = make_action(self, "Rewind", "anim-first", self.rewind, "F10", "Back to frame 0")
        self.play_action = make_action(self, "Play", "anim-play", self.play, "F11", "Play the animation (Animation mode) / keep accumulating")
        self.stop_action = make_action(self, "Stop", "anim-stop", self.stop, "F12", "Stop playing")
        self.stop_action.setEnabled(False)
        self.time_label = QLabel("Time: 0s:00f", self)
        self.time_label.setMinimumWidth(120)
        self.slider = QSlider(Qt.Orientation.Horizontal, self)
        self.slider.setMinimumWidth(200)
        self.slider.setToolTip("The current frame (right-click: timeline editor)")
        self.length_spin = QSpinBox(self)
        self.length_spin.setRange(1, 100000)
        self.length_spin.setSuffix(" s")
        self.length_spin.setToolTip("Animation length in seconds")
        self.fps_spin = QSpinBox(self)
        self.fps_spin.setRange(1, 240)
        self.fps_spin.setSuffix(" fps")
        self.fps_spin.setToolTip("Frames per second")
        self.slider.valueChanged.connect(self._on_slider)
        self.length_spin.valueChanged.connect(self._on_length)
        self.fps_spin.valueChanged.connect(self._on_fps)
        self.apply_settings(self.settings)

    # --- toolbars ------------------------------------------------------------------------------------------------------
    def mode_toolbar(self, parent) -> QToolBar:
        bar = QToolBar("Rendering mode", parent)
        bar.setObjectName("fragmentsRenderingMode")
        bar.setMovable(False)
        bar.addWidget(self.progressive_button)
        bar.addWidget(self.animation_button)
        for action in (self.rewind_action, self.play_action, self.stop_action):
            bar.addAction(action)
        return bar

    def time_toolbar(self, parent) -> QToolBar:
        bar = QToolBar("Time", parent)
        bar.setObjectName("fragmentsTime")
        bar.setMovable(False)
        bar.addWidget(self.time_label)
        bar.addWidget(self.slider)
        bar.addWidget(self.length_spin)
        bar.addWidget(self.fps_spin)
        return bar

    @property
    def actions_list(self) -> list[QAction]:
        return [self.rewind_action, self.play_action, self.stop_action]

    # --- settings ------------------------------------------------------------------------------------------------------
    def apply_settings(self, settings: AnimationSettings) -> None:
        """Show the clock settings (fps, length) without announcing them."""
        self.settings = settings
        with blocked(self.length_spin, self.fps_spin, self.slider):
            self.length_spin.setValue(settings.length)
            self.fps_spin.setValue(settings.fps)
            self.slider.setRange(0, settings.frames)
            self.slider.setSingleStep(1)
            self.slider.setPageStep(settings.fps)
            self.slider.setValue(min(self.frame, settings.frames))
        self._refresh_label()

    def set_keyframe_ticks(self, count: int) -> None:
        """Tick marks at the keyframes (FragM: `max / (k − 1)`), none when there are fewer than two."""
        if count > 1:
            self.slider.setTickInterval(max(1, self.settings.frames // (count - 1)))
            self.slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        else:
            self.slider.setTickPosition(QSlider.TickPosition.NoTicks)

    def _on_length(self, value: int) -> None:
        self.settings = self.settings.with_(length=value)
        self.apply_settings(self.settings)
        self.settings_changed.emit(self.settings)

    def _on_fps(self, value: int) -> None:
        self.settings = self.settings.with_(fps=value)
        self.apply_settings(self.settings)
        self.settings_changed.emit(self.settings)

    # --- mode / transport -------------------------------------------------------------------------------------------------
    def set_mode(self, mode: str) -> None:
        if mode == self.mode:
            return
        self.stop()
        self.mode = mode
        with blocked(self.progressive_button, self.animation_button):
            (self.animation_button if mode == ANIMATION else self.progressive_button).setChecked(True)
        self.mode_changed.emit(mode)

    @property
    def playing(self) -> bool:
        return self._playing

    def play(self) -> None:
        """Start the clock (Animation mode); in Progressive mode this only means "keep accumulating"."""
        if self._playing:
            return
        self._playing = True
        self._play_started_frame = self.frame if self.frame < self.settings.frames else 0
        self._play_started_at = time.perf_counter()
        self.play_action.setEnabled(False)
        self.stop_action.setEnabled(True)
        if self.mode == ANIMATION:
            self._clock.start()
        self.playing_changed.emit(True)

    def stop(self) -> None:
        if not self._playing:
            return
        self._playing = False
        self._clock.stop()
        self.play_action.setEnabled(True)
        self.stop_action.setEnabled(False)
        self.playing_changed.emit(False)

    def toggle_play(self) -> None:
        """Space in the viewport (FragM)."""
        self.stop() if self._playing else self.play()

    def rewind(self) -> None:
        was_playing = self._playing
        self.stop()
        self.set_frame(0)
        if was_playing:
            self.play()

    def set_frame(self, frame: int, announce: bool = True) -> None:
        """Move to `frame` (clamped); announces unless told not to."""
        frame = max(0, min(int(frame), self.settings.frames))
        self.frame = frame
        with blocked(self.slider):
            self.slider.setValue(frame)
        self._refresh_label()
        if announce:
            self.frame_changed.emit(frame)

    def _on_slider(self, value: int) -> None:
        if self._playing:
            self._play_started_frame, self._play_started_at = value, time.perf_counter()
        self.frame = value
        self._refresh_label()
        self.frame_changed.emit(value)

    def _tick(self) -> None:
        elapsed = time.perf_counter() - self._play_started_at
        frame = self._play_started_frame + int(elapsed * self.settings.fps)
        if frame >= self.settings.frames:
            if self.settings.loop_play:
                self._play_started_frame, self._play_started_at = 0, time.perf_counter()
                frame = 0
            else:
                self.set_frame(self.settings.frames)
                self.stop()
                return
        if frame != self.frame:
            self.set_frame(frame)

    def _refresh_label(self) -> None:
        fps = max(1, self.settings.fps)
        self.time_label.setText(f"Time: {self.frame // fps}s:{self.frame % fps:02d}f")

    def time(self) -> float:
        """The current frame in seconds (the `time` uniform)."""
        return self.settings.time_of(self.frame)


__all__ = ["AnimationControls", "PROGRESSIVE", "ANIMATION"]
