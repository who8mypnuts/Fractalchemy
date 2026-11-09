"""Draggable nodes, one per colour stop, drawn directly beneath the strip.

Mouse: press a node to select it and drag it anywhere (past its neighbours too); **double-click** an empty spot to add
a node there in the colour the gradient already has (so the gradient does not change); **right-click** a node for
its operations: add, add random, randomize, pick colour, delete. Right-clicking empty space offers *Add node here*.

Keys, once the bar or the strip has the focus (a click gives it): **Delete / Backspace** remove the selected node,
**← / →** nudge it by one Ultra Fractal index unit (**Shift**: ten), **Enter** opens the colour picker.

The operations are `NodeCommands`, shared with the *Selected node* panel.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QContextMenuEvent, QKeyEvent, QMouseEvent, QPainter, QPaintEvent, QPen, QPolygonF
from PySide6.QtWidgets import QMenu, QWidget

from .. import config
from ..ui.document import GradientDocument
from .mapping import PositionMapper
from .node_commands import NodeCommands
from .qt_colors import contrasting_pen_color, to_qcolor

NUDGE_KEYS = {Qt.Key.Key_Left: -1, Qt.Key.Key_Right: 1}


class NodeBar(QWidget):
    """Row of draggable node markers beneath the strip; drives selection, moves and the node gestures."""
    def __init__(self, document: GradientDocument, margin: int = config.EDITOR_MARGIN, parent=None,
                 commands: NodeCommands | None = None):
        """Args:
            document: Source of stops and selection; edits are sent back to it.
            margin: Horizontal inset matching the strip.
            parent: Qt parent.
            commands: The shared node operations (made here when not given).
        """
        super().__init__(parent)
        self._document = document
        self._margin = margin
        self._dragging = -1
        self.commands = commands if commands is not None else NodeCommands(document, self)
        self.setFixedHeight(config.NODE_BAR_HEIGHT)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setToolTip("Drag a node to move it · double-click to add one · right-click for more · "
                        "Del removes, ← / → nudge (Shift ×10), Enter picks the colour")
        document.gradient_replaced.connect(self.update)
        document.gradient_changed.connect(self.update)
        document.stop_changed.connect(self.update)
        document.selection_changed.connect(self.update)

    # --- geometry -----------------------------------------------------------
    def mapper(self) -> PositionMapper:
        """Position ↔ pixel mapping for the current width."""
        return PositionMapper(self.width(), self._margin)

    def node_center(self, index: int) -> QPointF:
        """Pixel centre of the marker for stop `index`."""
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

    def hit_reach(self) -> float:
        """The node hit radius in gradient units (0..1) — how close a double-click may land to an existing node."""
        return config.NODE_HIT_RADIUS / self.mapper().usable_width

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

    # --- mouse ----------------------------------------------------------------
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

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Double-click on empty space adds a node there in the existing colour (on a node: selects it)."""
        if event.button() != Qt.MouseButton.LeftButton:
            return
        index = self.node_at(event.position())
        if index >= 0:
            self._document.select(index)
        else:
            self.commands.add_at(self.mapper().to_position(event.position().x()), self.hit_reach())

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        self.menu_at(QPointF(event.pos())).exec(event.globalPos())

    def menu_at(self, pos: QPointF) -> QMenu:
        """The right-click menu for `pos`: a node's operations (the node gets selected), else *Add node here*."""
        index = self.node_at(pos)
        if index < 0:
            return add_here_menu(self, self.commands, self.mapper().to_position(pos.x()), self.hit_reach())
        self._document.select(index)
        menu = QMenu(self)
        self.commands.populate_menu(menu)
        return menu

    # --- keys -----------------------------------------------------------------
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if not handle_node_key(self.commands, event, self):
            super().keyPressEvent(event)


def handle_node_key(commands: NodeCommands, event: QKeyEvent, anchor: QWidget) -> bool:
    """The node keys (see the module docstring); True when `event` was one of them and was handled."""
    key = event.key()
    if commands.selected < 0:
        return False
    if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
        commands.delete()
    elif key in NUDGE_KEYS:
        coarse = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        commands.nudge(NUDGE_KEYS[key] * (config.NODE_NUDGE_COARSE if coarse else 1))
    elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
        commands.pick_colour(anchor)
    else:
        return False
    event.accept()
    return True


def add_here_menu(parent: QWidget, commands: NodeCommands, position: float, reach: float) -> QMenu:
    """The right-click menu of empty gradient space: *Add node here* (the double-click gesture)."""
    menu = QMenu(parent)
    action = menu.addAction("Add node here")
    action.setToolTip("Add a node at this position in the colour already there (double-click does the same)")
    action.triggered.connect(lambda _checked=False: commands.add_at(position, reach))
    return menu


def _pointer_triangle(center: QPointF, radius: int) -> QPolygonF:
    """Small upward tick so the node visibly points at its colour in the strip."""
    top = QPointF(center.x(), 0)
    return QPolygonF([top, QPointF(center.x() - radius, center.y()), QPointF(center.x() + radius, center.y())])


__all__ = ["NodeBar", "handle_node_key", "add_here_menu", "NUDGE_KEYS"]
