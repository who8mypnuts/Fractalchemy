"""A hue (angle) / saturation (radius) colour wheel you can click and drag on."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QConicalGradient, QMouseEvent, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget

HUE_STEPS = 24


class HueSatWheel(QWidget):
    """Colour wheel: hue by angle, saturation by radius.

    Signals:
        changed(float, float): Hue and saturation (0..1) after a click or drag.
    """
    changed = Signal(float, float)

    def __init__(self, diameter: int = 160, parent: QWidget | None = None):
        """Args:
            diameter: Widget size in pixels.
            parent: Qt parent.
        """
        super().__init__(parent)
        self._hue, self._sat = 0.0, 1.0
        self.setFixedSize(diameter, diameter)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def set_hue_sat(self, hue: float, sat: float) -> None:
        """Move the handle programmatically (no signal)."""
        self._hue, self._sat = hue % 1.0, max(0.0, min(1.0, sat))
        self.update()

    # --- geometry -----------------------------------------------------------
    def _center(self) -> QPointF:
        return QPointF(self.width() / 2, self.height() / 2)

    def _radius(self) -> float:
        return min(self.width(), self.height()) / 2 - 4

    def _handle(self) -> QPointF:
        angle = self._hue * 2 * math.pi
        r = self._sat * self._radius()
        c = self._center()
        return QPointF(c.x() + r * math.cos(angle), c.y() - r * math.sin(angle))

    # --- painting -----------------------------------------------------------
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        c, r = self._center(), self._radius()
        disc = QRectF(c.x() - r, c.y() - r, 2 * r, 2 * r)
        hues = QConicalGradient(c, 0)
        for i in range(HUE_STEPS + 1):
            hues.setColorAt(i / HUE_STEPS, QColor.fromHslF((i / HUE_STEPS) % 1.0, 1.0, 0.5))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(hues)
        painter.drawEllipse(disc)
        whiteness = QRadialGradient(c, r)
        whiteness.setColorAt(0.0, QColor(255, 255, 255, 255))
        whiteness.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(whiteness)
        painter.drawEllipse(disc)
        painter.setPen(QPen(QColor(60, 60, 60), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(disc)
        handle = self._handle()
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.drawEllipse(handle, 6, 6)
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.drawEllipse(handle, 6, 6)

    # --- interaction --------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._pick(event.position())

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._pick(event.position())

    def _pick(self, pos: QPointF) -> None:
        c = self._center()
        dx, dy = pos.x() - c.x(), c.y() - pos.y()
        self._hue = (math.atan2(dy, dx) / (2 * math.pi)) % 1.0
        self._sat = min(1.0, math.hypot(dx, dy) / self._radius())
        self.update()
        self.changed.emit(self._hue, self._sat)
