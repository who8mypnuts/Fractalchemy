"""Paints the current gradient as a horizontal band.

Double-click adds a node at that position in the colour already there (the gradient does not change); right-click
offers the same as *Add node here*. Keyboard focus goes to the node bar beneath (its focus proxy), so the node keys work
after clicking either.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QContextMenuEvent, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QMenu, QWidget

from .. import config
from ..ui.document import GradientDocument
from .mapping import PositionMapper
from .node_bar import NodeBar, add_here_menu
from .qt_colors import to_qgradient
from .theming import theme_color


class GradientStrip(QWidget):
    """Paints the document's gradient as a horizontal band."""
    def __init__(self, document: GradientDocument, margin: int = config.EDITOR_MARGIN, parent=None):
        """Args:
            document: Source of the gradient; repaints on its change signals.
            margin: Horizontal inset so edge nodes line up with the node bar.
            parent: Qt parent.
        """
        super().__init__(parent)
        self._document = document
        self._margin = margin
        self._nodes: NodeBar | None = None
        self.setMinimumHeight(config.STRIP_MIN_HEIGHT)
        self.setToolTip("Double-click to add a node in the colour already there")
        document.gradient_replaced.connect(self.update)
        document.gradient_changed.connect(self.update)
        document.stop_changed.connect(self.update)

    def attach_nodes(self, nodes: NodeBar) -> None:
        """The node bar beneath: it receives the strip's double-clicks and keyboard focus."""
        self._nodes = nodes
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setFocusProxy(nodes)

    def mapper(self) -> PositionMapper:
        """Position ↔ pixel mapping for the current width."""
        return PositionMapper(self.width(), self._margin)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if self._nodes is not None and event.button() == Qt.MouseButton.LeftButton and self._document.gradient.stops:
            self._nodes.commands.add_at(self.mapper().to_position(event.position().x()), self._nodes.hit_reach())

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        menu = self.menu_at(event.pos().x())
        if menu is not None:
            menu.exec(event.globalPos())

    def menu_at(self, x: float) -> QMenu | None:
        """The right-click menu at pixel `x`: *Add node here* (None without a gradient or a node bar)."""
        if self._nodes is None or not self._document.gradient.stops:
            return None
        return add_here_menu(self, self._nodes.commands, self.mapper().to_position(x), self._nodes.hit_reach())

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
        painter.fillRect(rect, theme_color("canvas_bg"))
        painter.setPen(theme_color("canvas_text"))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Open a .flame, .ugr or image file")
