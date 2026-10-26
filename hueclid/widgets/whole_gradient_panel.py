"""Controls that act on the gradient as a whole: rotate / HSL sliders and node operations."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QGridLayout, QGroupBox, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from .. import config
from ..formats.clipboard import gradient_to_text, text_to_gradient
from ..model import ColorStop, Gradient, simplify
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
    status = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Whole gradient", parent)
        self._document: GradientDocument | None = None
        self.position = AdjustRow("Position", -ROTATION_RANGE, ROTATION_RANGE, parent=self)
        self.hue = AdjustRow("Hue", -180, 180, "°", self)
        self.saturation = AdjustRow("Saturation", -100, 100, "%", self)
        self.luminance = AdjustRow("Luminance", -100, 100, "%", self)
        self.buttons: dict[str, QPushButton] = {}
        self.copy_button = QPushButton("Copy gradient", self)
        self.paste_button = QPushButton("Paste gradient", self)
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
        self.copy_button.setToolTip("Copy this gradient to the clipboard as Ultra Fractal / Apophysis gradient text")
        self.paste_button.setToolTip("Replace this gradient with the one on the clipboard")
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        self.paste_button.clicked.connect(self.paste_from_clipboard)
        QGuiApplication.clipboard().dataChanged.connect(self._refresh_enabled)
        row = len(OPERATIONS) // BUTTON_COLUMNS
        buttons.addWidget(self.copy_button, row, 0)
        buttons.addWidget(self.paste_button, row, 1)
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

    # --- clipboard ----------------------------------------------------------
    def copy_to_clipboard(self) -> None:
        if self._document is None or not self._document.gradient.stops:
            return
        QGuiApplication.clipboard().setText(gradient_to_text(self._document.gradient))
        self.status.emit(f"Copied '{self._document.gradient.name}' to the clipboard (UGR text)")

    def paste_from_clipboard(self) -> None:
        pasted = text_to_gradient(QGuiApplication.clipboard().text())
        if pasted is None or self._document is None:
            return self.status.emit("The clipboard doesn't hold a gradient")
        stops = simplify(pasted.stops, config.IMPORT_SIMPLIFY_TOLERANCE)
        self._document.apply_operation(lambda _g: stops)  # keeps this entry's name so Save stays in place
        self.status.emit(f"Pasted '{pasted.name}' ({len(stops)} nodes)")

    # --- state --------------------------------------------------------------
    def adjustments(self) -> Adjustments:
        return Adjustments(self.position.value(), self.hue.value(), self.saturation.value(), self.luminance.value())

    def reset(self) -> None:
        for row in self._rows():
            row.set_value(0)

    def _emit_adjustments(self, _value: int) -> None:
        self.adjustments_changed.emit(self.adjustments())

    def _refresh_enabled(self) -> None:
        has_gradient = self._document is not None and bool(self._document.gradient.stops)
        self.setEnabled(has_gradient or self._clipboard_has_gradient())
        for widget in (*self._rows(), *self.buttons.values(), self.copy_button):
            widget.setEnabled(has_gradient)
        self.paste_button.setEnabled(self._document is not None and self._clipboard_has_gradient())

    def _clipboard_has_gradient(self) -> bool:
        return text_to_gradient(QGuiApplication.clipboard().text()) is not None

    def _rows(self) -> tuple[AdjustRow, ...]:
        return self.position, self.hue, self.saturation, self.luminance
