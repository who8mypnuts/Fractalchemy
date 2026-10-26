"""Draggable nodes, one per colour stop, drawn directly beneath the strip."""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent, QPainter, QPaintEvent, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

from .. import config
from ..ui.document import GradientDocument
from .mapping import PositionMapper
from .qt_colors import contrasting_pen_color, to_qcolor


class NodeBar(QWidget):
    def __init__(self, document: GradientDocument, margin: int = config.EDITOR_MARGIN, parent=None):
        super().__init__(parent)
        self._document = document
        self._margin = margin
        self._dragging = -1
        self.setFixedHeight(config.NODE_BAR_HEIGHT)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        document.gradient_replaced.connect(self.update)
        document.stop_changed.connect(self.update)
        document.selection_changed.connect(self.update)

    # --- geometry -----------------------------------------------------------
    def mapper(self) -> PositionMapper:
        return PositionMapper(self.width(), self._margin)

    def node_center(self, index: int) -> QPointF:
        x = self.mapper().to_x(self._document.gradient.stops[index].position)
        return QPointF(x, config.NODE_RADIUS + 2)

    def node_at(self, pos: QPointF) -> int:
        """Index of the nearest node within reach of `pos`; -1 if none.

        Nodes overlap on dense gradients, so the already-selected node wins
        ties to keep a drag from hopping between neighbours.
        """
        candidates = [
            (self._distance_to(index, pos), index != self._document.selected_index, index)
            for index in range(len(self._document.gradient.stops))
        ]
        in_reach = [c for c in candidates if c[0] <= config.NODE_HIT_RADIUS]
        return min(in_reach)[2] if in_reach else -1

    def _distance_to(self, index: int, pos: QPointF) -> float:
        delta = self.node_center(index) - pos
        return (delta.x() ** 2 + delta.y() ** 2) ** 0.5

    # --- painting -----------------------------------------------------------
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        selected = self._document.selected_index
        for index, stop in enumerate(self._document.gradient.stops):
            if index != selected:
                self._paint_node(painter, index, stop.color, highlighted=False)
        if 0 <= selected < len(self._document.gradient.stops):
            self._paint_node(painter, selected, self._document.gradient.stops[selected].color, highlighted=True)

    def _paint_node(self, painter: QPainter, index: int, color, highlighted: bool) -> None:
        center = self.node_center(index)
        radius = config.NODE_RADIUS + (2 if highlighted else 0)
        painter.setBrush(to_qcolor(color))
        painter.setPen(QPen(contrasting_pen_color(color), 2 if highlighted else 1))
        painter.drawPolygon(_pointer_triangle(center, radius))
        painter.drawEllipse(center, radius, radius)

    # --- interaction --------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        index = self.node_at(event.position())
        self._document.select(index)
        self._dragging = index

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging < 0:
            return
        position = self.mapper().to_position(event.position().x())
        self._dragging = self._document.move_stop(self._dragging, position)  # index may change when crossing

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._dragging = -1


def _pointer_triangle(center: QPointF, radius: int) -> QPolygonF:
    """Small upward tick so the node visibly points at its colour in the strip."""
    top = QPointF(center.x(), 0)
    return QPolygonF([top, QPointF(center.x() - radius, center.y()), QPointF(center.x() + radius, center.y())])
