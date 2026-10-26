"""Controls that act on the gradient as a whole: rotate / HSL sliders and node operations."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QGroupBox, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from ..model import ColorStop, Gradient
from ..model import operations as ops
from ..model.adjust import ROTATION_RANGE, Adjustments
from ..ui.document import GradientDocument
from .adjust_row import AdjustRow

Operation = Callable[[Gradient], list[ColorStop]]

OPERATIONS: tuple[tuple[str, str, Operation], ...] = (
    ("Randomize nodes", "Scatter every node to a new random position (colours stay)", ops.randomize_positions),
    ("Randomize node colors", "Keep the nodes where they are; recolour them from a random harmony", ops.randomize_colors),
    ("Reroll gradient", "A whole new gradient: random node count, positions and colours", ops.reroll),
    ("Auto increase nodes", "Add a few nodes in colours that harmonise with the gradient", ops.add_nodes),
    ("Decrease nodes", "Randomly remove a share of the nodes", ops.remove_nodes),
    ("Smooth gradient", "Soften colour changes, keeping only the nodes that matter", ops.smooth),
)
BUTTON_COLUMNS = 3


class WholeGradientPanel(QGroupBox):
    """Built empty (promotable in Designer); call `bind()` once."""

    adjustments_changed = Signal(object)   # Adjustments
    operation_requested = Signal(object)   # Operation callable

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Whole gradient", parent)
        self._document: GradientDocument | None = None
        self.position = AdjustRow("Position", -ROTATION_RANGE, ROTATION_RANGE, parent=self)
        self.hue = AdjustRow("Hue", -180, 180, "°", self)
        self.saturation = AdjustRow("Saturation", -100, 100, "%", self)
        self.luminance = AdjustRow("Luminance", -100, 100, "%", self)
        self.buttons: dict[str, QPushButton] = {}
        self._build()
        for row in self._rows():
            row.value_changed.connect(self._emit_adjustments)

    # --- layout -------------------------------------------------------------
    def _build(self) -> None:
        self.position.setToolTip("Rotate the whole gradient; nodes wrap around the ends")
        hsl = QVBoxLayout()
        hsl.setContentsMargins(0, 0, 0, 0)
        for row in (self.hue, self.saturation, self.luminance):
            hsl.addWidget(row)
        buttons = QGridLayout()
        for i, (text, tip, operation) in enumerate(OPERATIONS):
            button = QPushButton(text, self)
            button.setToolTip(tip)
            button.clicked.connect(lambda _=False, op=operation: self.operation_requested.emit(op))
            buttons.addWidget(button, i // BUTTON_COLUMNS, i % BUTTON_COLUMNS)
            self.buttons[text] = button
        lower = QHBoxLayout()
        lower.addLayout(hsl, 1)        # sliders take about a third of the width…
        lower.addSpacing(16)
        lower.addLayout(buttons, 2)    # …and the buttons the rest
        layout = QVBoxLayout(self)
        layout.addWidget(self.position)
        layout.addLayout(lower)

    # --- document binding ---------------------------------------------------
    def bind(self, document: GradientDocument) -> None:
        if self._document is not None:
            raise RuntimeError("WholeGradientPanel is already bound to a document")
        self._document = document
        self.adjustments_changed.connect(document.set_adjustments)
        self.operation_requested.connect(document.apply_operation)
        document.adjustments_reset.connect(self.reset)
        document.gradient_replaced.connect(self.reset)
        document.gradient_replaced.connect(self._refresh_enabled)
        document.gradient_changed.connect(self._refresh_enabled)
        self._refresh_enabled()

    # --- state --------------------------------------------------------------
    def adjustments(self) -> Adjustments:
        return Adjustments(self.position.value(), self.hue.value(), self.saturation.value(), self.luminance.value())

    def reset(self) -> None:
        for row in self._rows():
            row.set_value(0)

    def _emit_adjustments(self, _value: int) -> None:
        self.adjustments_changed.emit(self.adjustments())

    def _refresh_enabled(self) -> None:
        self.setEnabled(self._document is not None and bool(self._document.gradient.stops))

    def _rows(self) -> tuple[AdjustRow, ...]:
        return self.position, self.hue, self.saturation, self.luminance
