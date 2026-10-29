"""The Formula Editor's smaller panels: the variation-preview options, the variable tools, the gradient presets button.

Each is a self-contained widget talking to the window through signals (or, for the variable tools, through the
`EditorContext` / document they are given), so the window only wires them up.
"""

from __future__ import annotations

import math
import random
from dataclasses import replace

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QGridLayout, QHBoxLayout,
                               QLabel, QLineEdit, QMenu, QPushButton, QSlider, QToolButton, QVBoxLayout, QWidget)

from ..formulas import authoring as A, workbench as W
from ..fractal import variations as V
from ..widgets.silent import blocked
from ..widgets.value_table import ValueRow
from .editor_context import EditorContext
from .editor_value_tabs import VariablesTab
from .formula_session import FormulaSession

SWEEP_PERIOD_MS = 4000
SWEEP_TICK_MS = 40
PREVIEW_SLIDERS = (("range", "Range", 1, 5, 2, "how far the grid reaches (± units)"), ("depth", "Depth", 1, 5, 1, "how many times the transform is applied"),
                   ("density", "Density", 1, 5, 2, "points per unit (× 5)"))


class PreviewOptions(QWidget):
    """Range / depth / density of the canvas's variation preview, and whether the input grid is drawn faintly.

    Signals:
        changed(): Any option changed.
    """
    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.sliders: dict[str, QSlider] = {}
        self.values: dict[str, QLabel] = {}
        self.show_inputs = QCheckBox("Show the input grid", self)
        self.show_inputs.setToolTip("Draw the grid the points start from faintly beneath the result")
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(6)
        for row, (key, title, low, high, default, tip) in enumerate(PREVIEW_SLIDERS):
            slider = QSlider(Qt.Orientation.Horizontal, self)
            slider.setRange(low, high)
            slider.setValue(default)
            slider.setToolTip(tip)
            value = QLabel(str(default), self)
            value.setMinimumWidth(14)
            grid.addWidget(QLabel(title, self), row, 0)
            grid.addWidget(slider, row, 1)
            grid.addWidget(value, row, 2)
            slider.valueChanged.connect(lambda v, label=value: (label.setText(str(v)), self.changed.emit()))
            self.sliders[key] = slider
            self.values[key] = value
        grid.addWidget(self.show_inputs, len(PREVIEW_SLIDERS), 0, 1, 3)
        grid.setColumnStretch(1, 1)
        self.show_inputs.toggled.connect(lambda _c: self.changed.emit())

    def settings(self) -> tuple[int, int, int, bool]:
        """(range, depth, density, show inputs)."""
        return (self.sliders["range"].value(), self.sliders["depth"].value(), self.sliders["density"].value(), self.show_inputs.isChecked())

    def set_settings(self, range_units: int, depth: int, density: int, show_inputs: bool) -> None:
        """Restore the options without announcing them."""
        with blocked(*self.sliders.values(), self.show_inputs):
            for key, value in (("range", range_units), ("depth", depth), ("density", density)):
                self.sliders[key].setValue(int(value))
                self.values[key].setText(str(self.sliders[key].value()))
            self.show_inputs.setChecked(bool(show_inputs))


class FormulaVariablesTab(VariablesTab):
    """The Variables tab with the scratch slot listed under the formula's own name."""

    def __init__(self, context: EditorContext, session: FormulaSession, parent: QWidget | None = None):
        super().__init__(context, parent)
        self.session = session
        self.show_all.hide()

    def rows(self) -> list[ValueRow]:
        """The selected transform's parameters, the formula's own under its real name; values left behind by a formula
        edited earlier (their names no longer declared) are not listed."""
        name = self.session.name or "formula"
        return [replace(row, info=name) if row.info == W.SCRATCH_NAME else row for row in super().rows() if row.info]


def parameter_span(info: V.ParamInfo | None, default: float) -> tuple[float, float]:
    """The range a sweep / randomise uses: the declared bounds, else a span around the default."""
    if info is not None and info.min is not None and info.max is not None and info.max > info.min:
        return float(info.min), float(info.max)
    span = max(1.0, abs(default)) * 2.0
    low, high = default - span, default + span
    if info is not None and info.type == "int":
        low, high = math.floor(low), math.ceil(high)
    return low, high


class VariableTools(QWidget):
    """The Variables table with *Reset*, *Randomise* and a *Sweep* that animates one variable over its range.

    Edits go to the document through the context (undoable; a sweep's steps coalesce into one step while it runs).
    """

    def __init__(self, context: EditorContext, session: FormulaSession, parent: QWidget | None = None):
        super().__init__(parent)
        self.context = context
        self.session = session
        self.table = FormulaVariablesTab(context, session, self)
        self.reset_button = QPushButton("Reset", self)
        self.reset_button.setToolTip("Every variable of the selected transform back to its default")
        self.random_button = QPushButton("Randomise", self)
        self.random_button.setToolTip("Random values within each variable's range (or around its default)")
        self.sweep_combo = QComboBox(self)
        self.sweep_combo.setToolTip("The variable the sweep animates")
        self.sweep_button = QPushButton("Sweep", self)
        self.sweep_button.setCheckable(True)
        self.sweep_button.setToolTip("Animate the chosen variable back and forth over its range, to see what it does")
        self._timer = QTimer(self, interval=SWEEP_TICK_MS)
        self._phase = 0.0
        buttons = QHBoxLayout()
        for b in (self.reset_button, self.random_button):
            buttons.addWidget(b)
        buttons.addWidget(self.sweep_combo, 1)
        buttons.addWidget(self.sweep_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.table, 1)
        layout.addLayout(buttons)
        self.reset_button.clicked.connect(self.reset_all)
        self.random_button.clicked.connect(self.randomise)
        self.sweep_button.toggled.connect(self._toggle_sweep)
        self._timer.timeout.connect(self._tick)

    @property
    def document(self):
        """The document the edits go to."""
        return self.context.document

    def refresh(self) -> None:
        """Show the selected transform's variables and list them in the sweep combo."""
        self.table.refresh()
        current = self.sweep_combo.currentText()
        with blocked(self.sweep_combo):
            self.sweep_combo.clear()
            self.sweep_combo.addItems(self.table.table.names())
            if current in self.table.table.names():
                self.sweep_combo.setCurrentText(current)
        enabled = self.sweep_combo.count() > 0
        for w in (self.reset_button, self.random_button, self.sweep_combo, self.sweep_button):
            w.setEnabled(enabled)
        if not enabled and self.sweep_button.isChecked():
            self.sweep_button.setChecked(False)

    def _declared(self) -> list[tuple[str, float, V.ParamInfo | None]]:
        """(key, default, info) of every variable the selected transform's variations declare."""
        xform = self.context.xform()
        if xform is None:
            return []
        out = []
        for name in xform.variations:
            var = V.REGISTRY.get(name)
            if var is not None:
                out += [(key, default, var.param_info.get(key)) for key, default in var.params.items()]
        return out

    def reset_all(self) -> None:
        """Every variable back to its default."""
        for key, default, _info in self._declared():
            self.document.set_param(self.context.selected, key, default)

    def randomise(self, rng: random.Random | None = None) -> None:
        """Random values within each variable's range (integers stay integral)."""
        rng = rng or random.Random()
        for key, default, info in self._declared():
            low, high = parameter_span(info, default)
            value = rng.uniform(low, high)
            if info is not None and info.type == "int":
                value = int(round(value)) or (1 if info.nonzero else 0)
            self.document.set_param(self.context.selected, key, value)

    @property
    def sweeping(self) -> bool:
        """True while the sweep runs."""
        return self._timer.isActive()

    def _toggle_sweep(self, on: bool) -> None:
        if on and self.sweep_combo.currentText():
            self._phase = 0.0
            self._timer.start()
        else:
            self._timer.stop()
            if self.sweep_button.isChecked():
                self.sweep_button.setChecked(False)

    def _tick(self) -> None:
        key = self.sweep_combo.currentText()
        entry = next(((k, d, i) for k, d, i in self._declared() if k == key), None)
        if entry is None or self.context.xform() is None:
            self.sweep_button.setChecked(False)
            return
        _key, default, info = entry
        low, high = parameter_span(info, default)
        self._phase = (self._phase + SWEEP_TICK_MS / SWEEP_PERIOD_MS) % 1.0
        value = low + (high - low) * (0.5 - 0.5 * math.cos(2 * math.pi * self._phase))
        if info is not None and info.type == "int":
            value = int(round(value)) or (1 if info.nonzero else 0)
        self.document.set_param(self.context.selected, key, value)


class VariableDialog(QDialog):
    """*Insert variable…*: name, default, real / integer, optional bounds."""

    def __init__(self, stem: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Insert variable")
        self.name_edit = QLineEdit(self, placeholderText="e.g. power")
        self.default_box = QDoubleSpinBox(self)
        self.default_box.setRange(-1e6, 1e6)
        self.default_box.setDecimals(4)
        self.default_box.setValue(1.0)
        self.kind_combo = QComboBox(self)
        self.kind_combo.addItems(["real", "int"])
        self.bounded = QCheckBox("With bounds", self)
        self.min_box = QDoubleSpinBox(self)
        self.max_box = QDoubleSpinBox(self)
        for box, value in ((self.min_box, 0.0), (self.max_box, 10.0)):
            box.setRange(-1e6, 1e6)
            box.setDecimals(4)
            box.setValue(value)
            box.setEnabled(False)
        self.bounded.toggled.connect(self.min_box.setEnabled)
        self.bounded.toggled.connect(self.max_box.setEnabled)
        form = QFormLayout(self)
        form.addRow(f"Name ({stem}_…)", self.name_edit)
        form.addRow("Default", self.default_box)
        form.addRow("Type", self.kind_combo)
        form.addRow(self.bounded)
        form.addRow("Minimum", self.min_box)
        form.addRow("Maximum", self.max_box)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)
        self.name_edit.setFocus()

    @property
    def short_name(self) -> str:
        """The name typed (the formula's stem is prefixed by the caller)."""
        return self.name_edit.text().strip()

    @property
    def default(self) -> float:
        """The default value."""
        return self.default_box.value()

    @property
    def kind(self) -> str:
        """`real` or `int`."""
        return self.kind_combo.currentText()

    @property
    def bounds(self) -> tuple[float, float] | None:
        """(min, max) when bounds were asked for."""
        return (self.min_box.value(), self.max_box.value()) if self.bounded.isChecked() else None


class GradientPresetsButton(QToolButton):
    """A small ▾ button listing bright gradient presets and *Random*.

    Signals:
        gradient_chosen(object): A `Gradient` to apply.
    """
    gradient_chosen = Signal(object)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setText("Presets")
        self.setToolTip("A bright preset gradient, or a random one, without opening the Gradient Library")
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(self)
        for name in A.GRADIENT_PRESETS:
            menu.addAction(name, lambda n=name: self.gradient_chosen.emit(A.preset_gradient(n)))
        menu.addSeparator()
        menu.addAction("Random", lambda: self.gradient_chosen.emit(A.random_gradient()))
        self.setMenu(menu)


__all__ = ["PreviewOptions", "FormulaVariablesTab", "VariableTools", "VariableDialog", "GradientPresetsButton", "parameter_span",
           "PREVIEW_SLIDERS"]
