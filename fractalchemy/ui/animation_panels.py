"""The Animation window's side panel: the animation's settings and its keyframe list.

Both panels show an `Animation` (`show(...)`) and report what the user edits through signals; the
window applies the edits to the `AnimationDocument`, so the panels know nothing about documents,
files or the main window.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QPushButton, QSpinBox, QVBoxLayout, QWidget)

from ..animation.model import EASINGS, INTERPOLATIONS, MAX_FPS, MAX_FRAMES, Animation, Keyframe
from ..widgets.silent import blocked, set_value_silently, updating


class AnimationSettingsPanel(QGroupBox):
    """Name, frame rate, length (frames or seconds), interpolation, easing and loop.

    Signals:
        edited(dict): The changed setting(s) as `AnimationDocument.set_settings` keyword arguments.
    """
    edited = Signal(dict)

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Animation", parent)
        self.name_edit = QLineEdit(self)
        self.fps_box = QSpinBox(self)
        self.frames_box = QSpinBox(self)
        self.duration_box = QDoubleSpinBox(self)
        self.interpolation_box = QComboBox(self)
        self.easing_box = QComboBox(self)
        self.loop_check = QCheckBox("Loop", self)
        self._updating = False
        self._fps = 1
        self._build()
        self._connect()

    def _build(self) -> None:
        form = QFormLayout(self)
        self.name_edit.setToolTip("The animation's name (the default base name of rendered frames)")
        form.addRow("Name", self.name_edit)
        self.fps_box.setRange(1, MAX_FPS)
        self.fps_box.setToolTip("Frames per second")
        self.frames_box.setRange(1, MAX_FRAMES)
        self.frames_box.setToolTip("Length of the animation in frames (never shorter than the last keyframe)")
        self.duration_box.setRange(0.01, MAX_FRAMES)
        self.duration_box.setDecimals(2)
        self.duration_box.setSuffix(" s")
        self.duration_box.setToolTip("Length in seconds (sets the frame count)")
        for box in (self.fps_box, self.frames_box, self.duration_box):
            box.setKeyboardTracking(False)
        row = QHBoxLayout()
        row.addWidget(self.fps_box)
        row.addWidget(QLabel("fps", self))
        row.addWidget(self.frames_box, 1)
        row.addWidget(QLabel("frames", self))
        row.addWidget(self.duration_box, 1)
        form.addRow("Length", row)
        for key, label in INTERPOLATIONS:
            self.interpolation_box.addItem(label, key)
        self.interpolation_box.setToolTip("How the frames between keyframes are made")
        form.addRow("Interpolation", self.interpolation_box)
        for key, label in EASINGS:
            self.easing_box.addItem(label, key)
        self.easing_box.setToolTip("Slow down into / out of every keyframe")
        form.addRow("Easing", self.easing_box)
        self.loop_check.setToolTip("After the last keyframe, blend back to the first one at the end of the animation; playback repeats")
        form.addRow("", self.loop_check)

    def _connect(self) -> None:
        self.name_edit.editingFinished.connect(lambda: self._emit(name=self.name_edit.text().strip() or "animation"))
        self.fps_box.valueChanged.connect(lambda v: self._emit(fps=int(v)))
        self.frames_box.valueChanged.connect(lambda v: self._emit(total_frames=int(v)))
        self.duration_box.valueChanged.connect(lambda v: self._emit(total_frames=max(1, round(v * self._fps))))
        self.interpolation_box.currentIndexChanged.connect(lambda _i: self._emit(interpolation=self.interpolation_box.currentData()))
        self.easing_box.currentIndexChanged.connect(lambda _i: self._emit(easing=self.easing_box.currentData()))
        self.loop_check.toggled.connect(lambda on: self._emit(loop=bool(on)))

    def show(self, animation: Animation) -> None:   # type: ignore[override]
        """Show the animation's settings (no signals)."""
        self._fps = animation.fps
        with updating(self):
            if self.name_edit.text() != animation.name:
                self.name_edit.setText(animation.name)
            set_value_silently(self.fps_box, animation.fps)
            set_value_silently(self.frames_box, animation.total_frames)
            set_value_silently(self.duration_box, animation.duration)
            with blocked(self.interpolation_box, self.easing_box, self.loop_check):
                self.interpolation_box.setCurrentIndex(max(0, self.interpolation_box.findData(animation.interpolation)))
                self.easing_box.setCurrentIndex(max(0, self.easing_box.findData(animation.easing)))
                self.loop_check.setChecked(animation.loop)

    def _emit(self, **fields) -> None:
        if not self._updating:
            self.edited.emit(fields)


class KeyframePanel(QGroupBox):
    """The keyframe list and the selected keyframe's frame, name and buttons.

    Signals:
        keyframe_clicked(object): A keyframe was clicked (show it in the main window).
        keyframe_selected(object): The current row changed (keyboard navigation); the keyframe.
        frame_edited(int): The selected keyframe's frame box.
        name_edited(str): The selected keyframe's name box.
        show_requested(): *Show in main window*.
        update_requested(): *Update from main window*.
    """
    keyframe_clicked = Signal(object)
    keyframe_selected = Signal(object)
    frame_edited = Signal(int)
    name_edited = Signal(str)
    show_requested = Signal()
    update_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Keyframes", parent)
        self.list = QListWidget(self)
        self.frame_box = QSpinBox(self)
        self.name_edit = QLineEdit(self)
        self.show_button = QPushButton("Show in main window", self)
        self.update_button = QPushButton("Update from main window", self)
        self._keyframes: list[Keyframe] = []
        self._updating = False
        self._build()
        self._connect()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        self.list.setToolTip("Click a keyframe to show its fractal in the main window and move the playhead to it")
        layout.addWidget(self.list, 1)
        form = QFormLayout()
        self.frame_box.setRange(0, MAX_FRAMES)
        self.frame_box.setKeyboardTracking(False)
        self.frame_box.setToolTip("Move the selected keyframe to another frame (it stays between its neighbours)")
        form.addRow("Frame", self.frame_box)
        self.name_edit.setPlaceholderText("label")
        self.name_edit.setToolTip("A label for the keyframe")
        form.addRow("Name", self.name_edit)
        layout.addLayout(form)
        buttons = QHBoxLayout()
        self.show_button.setToolTip("Load the keyframe's fractal in the main window (like choosing another fractal)")
        self.update_button.setToolTip("Replace the keyframe's fractal with what the main window shows now")
        buttons.addWidget(self.show_button)
        buttons.addWidget(self.update_button)
        layout.addLayout(buttons)

    def _connect(self) -> None:
        self.list.itemClicked.connect(lambda item: self._emit_keyframe(self.keyframe_clicked, self.list.row(item)))
        self.list.currentRowChanged.connect(lambda row: self._emit_keyframe(self.keyframe_selected, row))
        self.frame_box.valueChanged.connect(lambda v: self._updating or self.frame_edited.emit(int(v)))
        self.name_edit.editingFinished.connect(lambda: self._updating or self.name_edited.emit(self.name_edit.text().strip()))
        self.show_button.clicked.connect(self.show_requested)
        self.update_button.clicked.connect(self.update_requested)

    def _emit_keyframe(self, signal, row: int) -> None:
        if 0 <= row < len(self._keyframes):
            signal.emit(self._keyframes[row])

    def show(self, animation: Animation, selected: Keyframe | None, can_update: bool) -> None:   # type: ignore[override]
        """List the keyframes, highlight `selected` and fill its boxes (no signals)."""
        self._keyframes = list(animation.keyframes)
        with blocked(self.list):
            self.list.clear()
            for i, key in enumerate(self._keyframes):
                item = QListWidgetItem(f"{i + 1}.  frame {key.frame}  ({animation.frame_to_seconds(key.frame):.2f} s)  —  {key.label}")
                item.setToolTip(f"{key.label}: {len(key.flame.xforms)} transforms" + (" + final" if key.flame.final else ""))
                self.list.addItem(item)
            self.list.setCurrentRow(self._keyframes.index(selected) if selected in self._keyframes else -1)
        self.show_selected(selected, can_update)

    def show_selected(self, selected: Keyframe | None, can_update: bool) -> None:
        """Fill the frame / name boxes for `selected` and enable the buttons accordingly (no signals)."""
        with updating(self):
            with blocked(self.list):
                self.list.setCurrentRow(self._keyframes.index(selected) if selected in self._keyframes else -1)
            enabled = selected is not None
            for w in (self.frame_box, self.name_edit, self.show_button):
                w.setEnabled(enabled)
            self.update_button.setEnabled(enabled and can_update)
            set_value_silently(self.frame_box, selected.frame if selected else 0)
            if self.name_edit.text() != (selected.name if selected else ""):
                self.name_edit.setText(selected.name if selected else "")

    def set_frame_value(self, frame: int) -> None:
        """Show the frame the keyframe actually got (after clamping between its neighbours)."""
        set_value_silently(self.frame_box, frame)


__all__ = ["AnimationSettingsPanel", "KeyframePanel"]
