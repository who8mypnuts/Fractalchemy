"""Paints the current gradient as a horizontal band."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from .. import config
from ..ui.document import GradientDocument
from .mapping import PositionMapper
from .qt_colors import to_qgradient


class GradientStrip(QWidget):
    def __init__(self, document: GradientDocument, margin: int = config.EDITOR_MARGIN, parent=None):
        super().__init__(parent)
        self._document = document
        self._margin = margin
        self.setMinimumHeight(config.STRIP_MIN_HEIGHT)
        document.gradient_replaced.connect(self.update)
        document.stop_changed.connect(self.update)

    def mapper(self) -> PositionMapper:
        return PositionMapper(self.width(), self._margin)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        rect = QRectF(self._margin, 0, self.mapper().usable_width, self.height())
        gradient = self._document.gradient
        if gradient.stops:
            painter.fillRect(rect, to_qgradient(gradient, rect.left(), rect.right()))
        else:
            self._paint_empty(painter, rect)
        painter.setPen(QPen(QColor(70, 70, 70)))
        painter.drawRect(rect.adjusted(0, 0, -1, -1))

    def _paint_empty(self, painter: QPainter, rect: QRectF) -> None:
        painter.fillRect(rect, QColor(40, 40, 40))
        painter.setPen(QColor(160, 160, 160))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Open a .flame, .ugr or image file")
