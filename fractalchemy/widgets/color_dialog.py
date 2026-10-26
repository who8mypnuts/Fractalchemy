"""Non-modal colour picker: wheel + HSL sliders + RGB / hex fields, emitting every change live."""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QSpinBox, QVBoxLayout, QWidget,
)

from ..model import RGB, hex_to_rgb, rgb_to_hex
from ..model.color import hsl_to_rgb, rgb_to_hsl
from .adjust_row import AdjustRow
from .hue_wheel import HueSatWheel


class ColorPickerDialog(QDialog):
    """Keeps hue/sat/lightness as the master state so slider moves never round-trip through RGB.

    Signals:
        color_changed(tuple): The RGB colour, on every adjustment.
        finished_with(bool): True on OK, False on Cancel (the colour has already been reverted).
    """

    color_changed = Signal(tuple)
    finished_with = Signal(bool)

    def __init__(self, parent: QWidget | None = None):
        """Build the wheel, sliders, RGB / hex fields and preview."""
        super().__init__(parent, Qt.WindowType.Tool)  # stays above the main window, movable, non-modal
        self.setWindowTitle("Node colour")
        self._h, self._s, self._l = 0.0, 0.0, 0.5
        self._original: RGB = (0, 0, 0)
        self._updating = False
        self.wheel = HueSatWheel(parent=self)
        self.hue = AdjustRow("Hue", 0, 359, "°", self)
        self.saturation = AdjustRow("Saturation", 0, 100, "%", self)
        self.lightness = AdjustRow("Lightness", 0, 100, "%", self)
        self.red, self.green, self.blue = (QSpinBox(self) for _ in range(3))
        self.hex = QLineEdit(self)
        self.before, self.after = QFrame(self), QFrame(self)
        self._build()
        self._connect()

    # --- API ----------------------------------------------------------------
    def set_color(self, color: RGB, as_original: bool = True) -> None:
        """Show `color`; with as_original=True it is what Cancel reverts to."""
        if as_original:
            self._original = color
            _paint(self.before, color)
        self._set_hsl(*rgb_to_hsl(color))

    def color(self) -> RGB:
        """The colour currently shown."""
        return hsl_to_rgb(self._h, self._s, self._l)

    def show_beside(self, anchor: QWidget) -> None:
        """Show (if hidden) next to `anchor`'s window and bring to front.

        The dialog is placed to the right of the window when the screen has room,
        otherwise over `anchor` itself — so it never covers the gradient.
        """
        if not self.isVisible():
            self.move(self._position_beside(anchor))
            self.show()
        self.raise_()
        self.activateWindow()

    # --- layout -------------------------------------------------------------
    def _build(self) -> None:
        for spin in (self.red, self.green, self.blue):
            spin.setRange(0, 255)
            spin.setFixedWidth(64)
        self.hex.setMaxLength(7)
        self.hex.setFixedWidth(80)
        for frame in (self.before, self.after):
            frame.setFixedSize(44, 28)
            frame.setFrameShape(QFrame.Shape.Box)
        rgb = QFormLayout()
        rgb.addRow("R", self.red)
        rgb.addRow("G", self.green)
        rgb.addRow("B", self.blue)
        rgb.addRow("Hex", self.hex)
        sliders = QVBoxLayout()
        for row in (self.hue, self.saturation, self.lightness):
            sliders.addWidget(row)
        preview = QHBoxLayout()
        preview.addWidget(QLabel("Before"))
        preview.addWidget(self.before)
        preview.addSpacing(12)
        preview.addWidget(QLabel("After"))
        preview.addWidget(self.after)
        preview.addStretch(1)
        sliders.addLayout(preview)
        top = QHBoxLayout()
        top.addWidget(self.wheel, 0, Qt.AlignmentFlag.AlignTop)
        top.addLayout(sliders, 1)
        top.addLayout(rgb)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(buttons)

    def _configure_fields(self) -> None:
        for spin in (self.red, self.green, self.blue):
            spin.setRange(0, 255)
            spin.setFixedWidth(64)
        self.hex.setMaxLength(7)
        self.hex.setFixedWidth(80)
        for frame in (self.before, self.after):
            frame.setFixedSize(44, 28)
            frame.setFrameShape(QFrame.Shape.Box)

    def _connect(self) -> None:
        self.wheel.changed.connect(lambda h, s: self._set_hsl(h, s, self._l))
        self.hue.value_changed.connect(lambda v: self._set_hsl(v / 360.0, self._s, self._l))
        self.saturation.value_changed.connect(lambda v: self._set_hsl(self._h, v / 100.0, self._l))
        self.lightness.value_changed.connect(lambda v: self._set_hsl(self._h, self._s, v / 100.0))
        for spin in (self.red, self.green, self.blue):
            spin.valueChanged.connect(self._from_rgb_fields)
        self.hex.editingFinished.connect(self._from_hex)

    # --- state --------------------------------------------------------------
    def _set_hsl(self, h: float, s: float, l: float) -> None:
        self._h, self._s, self._l = h % 1.0, max(0.0, min(1.0, s)), max(0.0, min(1.0, l))
        self._refresh_controls()
        self.color_changed.emit(self.color())

    def _from_rgb_fields(self, _value: int) -> None:
        if not self._updating:
            self._set_hsl(*rgb_to_hsl((self.red.value(), self.green.value(), self.blue.value())))

    def _from_hex(self) -> None:
        text = self.hex.text().strip().lstrip("#")
        if len(text) == 6:
            try:
                self._set_hsl(*rgb_to_hsl(hex_to_rgb(text)))
            except ValueError:
                pass

    def _refresh_controls(self) -> None:
        self._updating = True
        rgb = self.color()
        self.wheel.set_hue_sat(self._h, self._s)
        self.hue.set_value(round(self._h * 360) % 360)
        self.saturation.set_value(round(self._s * 100))
        self.lightness.set_value(round(self._l * 100))
        for spin, value in zip((self.red, self.green, self.blue), rgb):
            spin.setValue(value)
        self.hex.setText("#" + rgb_to_hex(rgb))
        _paint(self.after, rgb)
        self._updating = False

    def _position_beside(self, anchor: QWidget) -> QPoint:
        window = anchor.window()
        screen = QGuiApplication.screenAt(window.pos()) or QGuiApplication.primaryScreen()
        available = screen.availableGeometry()
        size = self.sizeHint()
        x = window.frameGeometry().right() + 8
        if x + size.width() > available.right():
            x = max(available.left(), window.frameGeometry().right() - size.width())
        y = min(anchor.mapToGlobal(QPoint(0, 0)).y(), available.bottom() - size.height())
        return QPoint(x, y)

    # --- closing ------------------------------------------------------------
    def accept(self) -> None:
        super().accept()
        self.finished_with.emit(True)

    def reject(self) -> None:
        self._set_hsl(*rgb_to_hsl(self._original))  # revert live
        super().reject()
        self.finished_with.emit(False)


def _paint(frame: QFrame, color: RGB) -> None:
    frame.setStyleSheet(f"background-color: {QColor(*color).name()};")
