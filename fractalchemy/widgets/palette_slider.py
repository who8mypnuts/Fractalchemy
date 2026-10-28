"""A palette strip with a draggable marker: the Transform Editor's colour chooser."""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from .images import palette_pixmap


class PaletteSlider(QWidget):
    """The palette as a strip with a marker at the transform colour; click or drag to choose.

    Signals:
        value_changed(float): The colour position (0..1) while dragging / on click.
    """
    value_changed = Signal(float)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._palette: list = []
        self._value = 0.0
        self._pixmap = None
        self.setMinimumHeight(26)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_palette(self, palette) -> None:
        """Show this palette (RGB triples)."""
        self._palette = list(palette)
        self._pixmap = None
        self.update()

    def value(self) -> float:
        """The marker's position, 0..1."""
        return self._value

    def set_value(self, value: float) -> None:
        """Move the marker (no signal)."""
        self._value = max(0.0, min(1.0, float(value)))
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        w, h = self.width(), self.height()
        if self._palette:
            if self._pixmap is None or self._pixmap.width() != w - 2:
                self._pixmap = palette_pixmap(self._palette, max(1, w - 2), h - 8)
            painter.drawPixmap(1, 1, self._pixmap)
        painter.setPen(QPen(QColor(90, 90, 90), 1))
        painter.drawRect(0, 0, w - 1, h - 7)
        x = 1 + self._value * (w - 3)
        painter.setPen(QPen(QColor(20, 20, 20), 1))
        painter.setBrush(QColor(240, 240, 240))
        painter.drawPolygon([QPointF(x, h - 8), QPointF(x - 5, h - 1), QPointF(x + 5, h - 1)])
        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._pick(event.position().x())

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._pick(event.position().x())

    def _pick(self, x: float) -> None:
        value = max(0.0, min(1.0, (x - 1) / max(1, self.width() - 3)))
        if value != self._value:
            self.set_value(value)
            self.value_changed.emit(self._value)


__all__ = ["PaletteSlider"]
