"""*Animate…* in the Parameters tab: keyframes of a script's result while one of its parameters sweeps.

The dialog asks for the range (from, to), the number of keyframes and their spacing, the easing and whether the
keyframes go into the animation being edited (from the playhead on) or a new one. The script runs once per keyframe on
the fractal as it was before its run, with the same random numbers (so only the animated parameter moves), restricted
(no side effects), on the thread pool; each result becomes a keyframe named "Angle = 45". Integer and dropdown
parameters get one keyframe per value between the two ends. The Animation window interpolates *between* keyframes, so
more keyframes follow a script that is not linear in its parameter more closely. The timeline has no undo, so replacing
keyframes that already exist on those frames is confirmed first.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QLabel, QMessageBox,
                               QSpinBox, QVBoxLayout, QWidget)

from ..scripting.explore import sweep
from ..scripting.parameters import ParamSpec
from ..scripting.runner import run_script
from .background import run_in_background

EASINGS = (("Even steps", "linear"), ("Ease in", "in"), ("Ease out", "out"), ("Ease in and out", "in-out"))
ANIMATE_RESTRICTION = "while it is animated"


def keyframe_plan(spec: ParamSpec, start: Any, end: Any, count: int, first: int, spacing: int, easing: str) -> list[tuple[int, Any]]:
    """(frame, value) for every keyframe (Qt-free)."""
    values = sweep(spec, start, end, count, easing)
    return [(first + i * max(1, int(spacing)), value) for i, value in enumerate(values)]


def render_keyframes(code: str, snapshot, seed: int, values: dict, name: str, plan: list[tuple[int, Any]]) -> list:
    """The script's flame for every planned value (runs on the thread pool); failures are skipped with a note."""
    out = []
    for frame, value in plan:
        result = run_script(code, snapshot, None, None, seed=seed, parameters={**values, name: value}, restricted=ANIMATE_RESTRICTION)
        out.append((frame, value, result.flame if result.ok and not result.refused else None,
                    result.refused or (str(result.error) if result.error else "")))
    return out


class AnimateParameterDialog(QDialog):
    """The dialog (see the module docstring)."""

    def __init__(self, live, name: str, animation_window, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(f"Animate {name}")
        self.live = live
        self.name = name
        self.animation = animation_window
        self.spec: ParamSpec = next(s for s in live.specs if s.name == name)
        self.result_count = 0
        self._build()

    def _value_box(self, value: Any) -> QWidget:
        spec = self.spec
        if spec.kind == "choice":
            box = QComboBox(self)
            box.addItems([str(c) for c in spec.choices])
            box.setCurrentIndex(spec.choices.index(value) if value in spec.choices else 0)
            return box
        if spec.kind == "bool":
            box = QCheckBox(self)
            box.setChecked(bool(value))
            return box
        box = QSpinBox(self) if spec.kind == "int" else QDoubleSpinBox(self)
        if spec.kind == "float":
            box.setDecimals(spec.decimals)
        box.setRange(spec.minimum if spec.minimum is not None else -1e9, spec.maximum if spec.maximum is not None else 1e9)
        box.setValue(value)
        return box

    def _read(self, box: QWidget) -> Any:
        if isinstance(box, QComboBox):
            return self.spec.choices[box.currentIndex()]
        if isinstance(box, QCheckBox):
            return box.isChecked()
        return box.value()

    def _build(self) -> None:
        spec, current = self.spec, self.live.values.get(self.name, self.spec.default)
        end = spec.maximum if spec.kind in ("float", "int") and spec.maximum is not None else (
            spec.choices[-1] if spec.kind == "choice" else (not current if spec.kind == "bool" else current))
        self.start_box, self.end_box = self._value_box(current), self._value_box(end)
        self.count_box = QSpinBox(self)
        self.count_box.setRange(2, 120)
        self.count_box.setValue(5)
        self.count_box.setEnabled(spec.kind == "float")
        document = self.animation.document
        fps = max(1, int(document.animation.fps))
        self.first_box = QSpinBox(self)
        self.first_box.setRange(0, 100000)
        self.first_box.setValue(document.frame)
        self.spacing_box = QSpinBox(self)
        self.spacing_box.setRange(1, 10000)
        self.spacing_box.setValue(max(1, fps // 2))
        self.easing_box = QComboBox(self)
        for text, key in EASINGS:
            self.easing_box.addItem(text, key)
        self.easing_box.setEnabled(spec.kind == "float")
        self.target_box = QComboBox(self)
        self.target_box.addItems(["Add to the animation being edited", "Start a new animation"])
        note = QLabel("The Animation window blends <i>between</i> keyframes: more keyframes follow the script more closely.", self)
        note.setWordWrap(True)
        form = QFormLayout()
        form.addRow("From", self.start_box)
        form.addRow("To", self.end_box)
        form.addRow("Keyframes", self.count_box)
        form.addRow("First frame", self.first_box)
        form.addRow("Frames between keyframes", self.spacing_box)
        form.addRow("Steps", self.easing_box)
        form.addRow("Keyframes go", self.target_box)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Create keyframes")
        buttons.accepted.connect(self.create)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(note)
        layout.addWidget(buttons)

    def plan(self) -> list[tuple[int, Any]]:
        new = self.target_box.currentIndex() == 1
        return keyframe_plan(self.spec, self._read(self.start_box), self._read(self.end_box), self.count_box.value(),
                             0 if new else self.first_box.value(), self.spacing_box.value(), self.easing_box.currentData())

    def create(self) -> None:
        """Run the script for every keyframe (on the thread pool) and add the keyframes when they are ready."""
        plan = self.plan()
        document = self.animation.document
        new = self.target_box.currentIndex() == 1
        if not new:
            taken = {k.frame for k in document.animation.keyframes} & {frame for frame, _v in plan}
            if taken and QMessageBox.question(self, self.windowTitle(), f"Replace {len(taken)} keyframe{'s' if len(taken) != 1 else ''} "
                                              "already on those frames? (The timeline has no undo.)") != QMessageBox.StandardButton.Yes:
                return
        session = self.live.session
        self.setEnabled(False)
        run_in_background(render_keyframes, session.code, session.snapshot, session.seed, dict(self.live.values), self.name, plan,
                          on_done=lambda results: self._add(results, new),
                          on_error=lambda exc: (self.setEnabled(True), QMessageBox.warning(self, self.windowTitle(), str(exc))))

    def _add(self, results: list, new: bool) -> None:
        document = self.animation.document
        if new:
            if not self.animation.confirm_discard():
                self.setEnabled(True)
                return
            document.new()
        failures = []
        for frame, value, flame, error in results:
            if flame is None:
                failures.append(f"{self.name} = {value}: {error}")
                continue
            document.capture(flame, frame, f"{self.name} = {value:.4g}" if isinstance(value, float) else f"{self.name} = {value}")
            self.result_count += 1
        if failures:
            QMessageBox.warning(self, self.windowTitle(), "Some keyframes could not be made:\n" + "\n".join(failures[:8]))
        if results:
            document.set_frame(results[0][0])
        self.animation.bring_to_front()
        self.accept()


__all__ = ["AnimateParameterDialog", "keyframe_plan", "render_keyframes"]
