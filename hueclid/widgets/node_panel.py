"""Controls for the selected node: number, colour, add / randomise / delete."""

from __future__ import annotations

import random

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtWidgets import QAbstractSpinBox, QFormLayout, QGroupBox, QPushButton, QSlider, QSpinBox, QVBoxLayout, QWidget

from .. import config
from ..model import RGB, rgb_to_hex
from ..model import node_ops
from ..ui.document import GradientDocument
from .color_dialog import ColorPickerDialog
from .qt_colors import contrasting_pen_color

PANEL_WIDTH = 210
POSITION_MAX = config.UGR_MAX_INDEX  # 0..399, Ultra Fractal's native gradient index units


class NodePanel(QGroupBox):
    """Built empty (promotable in Designer); call `bind()` once. Greyed out with no selection."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Selected node", parent)
        self._document: GradientDocument | None = None
        self._rng = random.Random()
        self.number = QSpinBox(self)
        self.swatch = QPushButton(self)
        self.position = QSpinBox(self)
        self.position_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.add_button = QPushButton("Add node", self)
        self.add_random_button = QPushButton("Add random node", self)
        self.randomize_button = QPushButton("Randomize node", self)
        self.delete_button = QPushButton("Delete node", self)
        self.picker = ColorPickerDialog(self)
        self._build()
        self._connect()
        self.setEnabled(False)

    # --- layout -------------------------------------------------------------
    def _build(self) -> None:
        self.setFixedWidth(PANEL_WIDTH)
        self.number.setRange(1, 1)
        self.number.setToolTip("Node number — type one to select it")
        self.number.setKeyboardTracking(False)
        self.position.setRange(0, POSITION_MAX)
        self.position.setToolTip(f"Node position, 0–{POSITION_MAX} (Ultra Fractal index units)")
        self.position.setKeyboardTracking(False)
        self.position.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
        self.position_slider.setRange(0, POSITION_MAX)
        self.position_slider.setTracking(True)
        self.position_slider.setToolTip("Drag to move this node along the gradient")
        self.swatch.setFixedHeight(36)
        self.swatch.setToolTip("Click to change this node's colour")
        self.swatch.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_button.setToolTip("Insert a node after this one, in the same colour")
        self.add_random_button.setToolTip("Insert a node after this one, in an entirely new colour")
        self.randomize_button.setToolTip("Nudge this node's hue, saturation and lightness at random")
        self.delete_button.setToolTip("Remove this node")
        form = QFormLayout()
        form.addRow("Node", self.number)
        form.addRow("Position", self.position)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.position_slider)
        colour = QFormLayout()
        colour.addRow("Colour", self.swatch)
        layout.addLayout(colour)
        for button in (self.add_button, self.add_random_button, self.randomize_button, self.delete_button):
            layout.addWidget(button)
        layout.addStretch(1)

    def _connect(self) -> None:
        self.number.valueChanged.connect(lambda n: self._document.select(n - 1) if self._document else None)
        self.position.valueChanged.connect(self._move_to)
        self.position_slider.valueChanged.connect(self._move_to)
        self.swatch.clicked.connect(self.open_picker)
        self.add_button.clicked.connect(lambda: self._insert(self._current_color()))
        self.add_random_button.clicked.connect(lambda: self._insert(node_ops.random_color(self._rng)))
        self.randomize_button.clicked.connect(self._randomize)
        self.delete_button.clicked.connect(self._delete)
        self.picker.color_changed.connect(self._set_color)

    # --- binding ------------------------------------------------------------
    def bind(self, document: GradientDocument) -> None:
        if self._document is not None:
            raise RuntimeError("NodePanel is already bound to a document")
        self._document = document
        document.selection_changed.connect(self._refresh)
        document.stop_changed.connect(lambda _i: self._refresh())
        document.gradient_changed.connect(self._refresh)
        document.gradient_replaced.connect(self._refresh)
        self._refresh()

    # --- actions ------------------------------------------------------------
    def open_picker(self) -> None:
        index = self._selected()
        if index < 0:
            return
        self.picker.set_color(self._current_color(), as_original=True)
        if not self.picker.isVisible():
            self.picker.move(self._picker_position())
            self.picker.show()
        self.picker.raise_()
        self.picker.activateWindow()

    def _insert(self, color: RGB) -> None:
        index = self._selected()
        if index >= 0:
            stops, new_index = node_ops.inserted_after(self._document.gradient, index, color)
            self._document.insert_stop(stops, new_index)

    def _randomize(self) -> None:
        if self._selected() >= 0:
            self._set_color(node_ops.perturbed_color(self._current_color(), self._rng))

    def _delete(self) -> None:
        index = self._selected()
        if index >= 0 and self.delete_button.isEnabled():
            self._document.remove_stop(index)

    def _move_to(self, units: int) -> None:
        index = self._selected()
        if index >= 0 and round(self._document.gradient.stops[index].position * POSITION_MAX) != units:
            self._document.move_stop(index, units / POSITION_MAX)  # selection follows if it crosses a neighbour

    def _set_color(self, color: RGB) -> None:
        index = self._selected()
        if index >= 0 and self._document.gradient.stops[index].color != tuple(color):
            self._document.set_color(index, tuple(color))

    # --- presentation -------------------------------------------------------
    def _refresh(self, *_args) -> None:
        index = self._selected()
        stops = self._document.gradient.stops if self._document else []
        active = 0 <= index < len(stops)
        self.setEnabled(active)
        if not active:
            if self.picker.isVisible():
                self.picker.hide()
            return
        stop = stops[index]
        self.number.blockSignals(True)
        self.number.setRange(1, len(stops))
        self.number.setValue(index + 1)
        self.number.blockSignals(False)
        units = round(stop.position * POSITION_MAX)
        for widget in (self.position, self.position_slider):
            widget.blockSignals(True)
            widget.setValue(units)
            widget.blockSignals(False)
        self.delete_button.setEnabled(len(stops) > node_ops.MIN_NODES)
        self._paint_swatch(stop.color)
        if self.picker.isVisible() and self.picker.color() != stop.color:
            self.picker.set_color(stop.color, as_original=True)  # selection moved: retarget the picker

    def _paint_swatch(self, color: RGB) -> None:
        text = contrasting_pen_color(color).name()
        self.swatch.setText("#" + rgb_to_hex(color))
        self.swatch.setStyleSheet(f"background-color: {QColor(*color).name()}; color: {text}; border: 1px solid #555;")

    def _picker_position(self) -> QPoint:
        """Beside the main window when the screen allows, otherwise over this panel (never over the gradient)."""
        window = self.window()
        screen = QGuiApplication.screenAt(window.pos()) or QGuiApplication.primaryScreen()
        available = screen.availableGeometry()
        size = self.picker.sizeHint()
        x = window.frameGeometry().right() + 8
        if x + size.width() > available.right():
            x = max(available.left(), window.frameGeometry().right() - size.width())
        y = min(self.mapToGlobal(QPoint(0, 0)).y(), available.bottom() - size.height())
        return QPoint(x, y)

    # --- helpers ------------------------------------------------------------
    def _selected(self) -> int:
        return self._document.selected_index if self._document else -1

    def _current_color(self) -> RGB:
        return self._document.gradient.stops[self._selected()].color
