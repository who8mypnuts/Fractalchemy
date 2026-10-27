"""A Chaotica-style tone-curve editor: one square canvas, a channel selector and reset buttons.

Click on empty canvas to add a control point, drag points to move them (end points slide only
vertically, others stay between their neighbours), right-click a point to remove it. The curve is the
monotone cubic of `fractal/curves.py`, drawn with the other channels shown faintly for reference.

    editor.set_curves(curves)              # show (a copy is kept)
    editor.curve_changed.connect(fn)       # fn(channel, points) on every change, live while dragging
    editor.channel_reset.connect(fn)       # fn(channel) when a reset button was used
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QMouseEvent, QPainter, QPainterPath, QPaintEvent, QPen
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QSizePolicy, QToolButton, QVBoxLayout, QWidget

from ..fractal.curves import CHANNELS, DEFAULT_POINTS, Curves, monotone_cubic

CHANNEL_LABELS = {"overall": "All", "red": "R", "green": "G", "blue": "B", "alpha": "A"}
CHANNEL_COLORS = {"overall": QColor(230, 230, 230), "red": QColor(235, 80, 80), "green": QColor(80, 200, 90),
                  "blue": QColor(90, 130, 255), "alpha": QColor(200, 170, 255)}
HIT_RADIUS = 8.0
POINT_RADIUS = 4.0
MARGIN = 6.0
MIN_POINT_GAP = 0.005


class CurveCanvas(QWidget):
    """The square drawing / dragging surface."""
    points_changed = Signal(str, list)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._curves = Curves()
        self._channel = "overall"
        self._drag: int | None = None
        self.setMinimumSize(120, 120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setToolTip("Click: add a point · drag: move · right-click: remove")

    def heightForWidth(self, width: int) -> int:
        return width

    def hasHeightForWidth(self) -> bool:
        return True

    # --- state ----------------------------------------------------------------------------------------------
    def set_curves(self, curves: Curves) -> None:
        self._curves = curves.copy()
        self.update()

    def curves(self) -> Curves:
        return self._curves

    def channel(self) -> str:
        return self._channel

    def set_channel(self, channel: str) -> None:
        self._channel = channel
        self.update()

    def points(self) -> list[tuple[float, float]]:
        return list(self._curves.points[self._channel])

    # --- geometry -------------------------------------------------------------------------------------------
    def _area(self) -> QRectF:
        side = min(self.width(), self.height()) - 2 * MARGIN
        return QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)

    def _to_screen(self, x: float, y: float) -> QPointF:
        a = self._area()
        return QPointF(a.left() + x * a.width(), a.bottom() - y * a.height())

    def _from_screen(self, pos: QPointF) -> tuple[float, float]:
        a = self._area()
        x = (pos.x() - a.left()) / a.width() if a.width() else 0.0
        y = (a.bottom() - pos.y()) / a.height() if a.height() else 0.0
        return min(1.0, max(0.0, x)), min(1.0, max(0.0, y))

    def _hit(self, pos: QPointF) -> int | None:
        best, best_d = None, HIT_RADIUS
        for i, (x, y) in enumerate(self.points()):
            p = self._to_screen(x, y)
            d = ((p.x() - pos.x()) ** 2 + (p.y() - pos.y()) ** 2) ** 0.5
            if d <= best_d:
                best, best_d = i, d
        return best

    # --- painting -------------------------------------------------------------------------------------------
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        a = self._area()
        painter.fillRect(a, QColor(28, 28, 30))
        painter.setPen(QPen(QColor(60, 60, 64), 1))
        for i in range(1, 4):
            x = a.left() + a.width() * i / 4
            y = a.top() + a.height() * i / 4
            painter.drawLine(QPointF(x, a.top()), QPointF(x, a.bottom()))
            painter.drawLine(QPointF(a.left(), y), QPointF(a.right(), y))
        painter.setPen(QPen(QColor(80, 80, 84), 1, Qt.PenStyle.DashLine))
        painter.drawLine(self._to_screen(0, 0), self._to_screen(1, 1))
        for channel in CHANNELS:
            if channel != self._channel and not self._curves.is_default(channel):
                self._draw_curve(painter, channel, faint=True)
        self._draw_curve(painter, self._channel, faint=False)
        painter.setPen(QPen(QColor(90, 90, 94), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(a)
        painter.end()

    def _draw_curve(self, painter: QPainter, channel: str, faint: bool) -> None:
        color = QColor(CHANNEL_COLORS[channel])
        if faint:
            color.setAlpha(90)
        steps = max(32, int(self._area().width()))
        xs = [i / steps for i in range(steps + 1)]
        ys = monotone_cubic(self._curves.points[channel], xs)
        path = QPainterPath(self._to_screen(xs[0], ys[0]))
        for x, y in zip(xs[1:], ys[1:]):
            path.lineTo(self._to_screen(x, y))
        painter.setPen(QPen(color, 1.0 if faint else 2.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        if not faint:
            painter.setPen(QPen(QColor(20, 20, 20), 1))
            painter.setBrush(QBrush(color))
            for x, y in self._curves.points[channel]:
                painter.drawEllipse(self._to_screen(x, y), POINT_RADIUS, POINT_RADIUS)

    # --- mouse ----------------------------------------------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:
        pos = event.position()
        hit = self._hit(pos)
        pts = self.points()
        if event.button() == Qt.MouseButton.RightButton:
            if hit is not None and 0 < hit < len(pts) - 1:
                del pts[hit]
                self._commit(pts)
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if hit is None:
            x, y = self._from_screen(pos)
            pts.append((x, y))
            pts.sort()
            hit = pts.index((x, y))
            self._commit(pts)
        self._drag = hit

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag is None:
            return
        pts = self.points()
        x, y = self._from_screen(event.position())
        i = self._drag
        if i == 0:
            x = 0.0
        elif i == len(pts) - 1:
            x = 1.0
        else:
            x = min(max(x, pts[i - 1][0] + MIN_POINT_GAP), pts[i + 1][0] - MIN_POINT_GAP)
        pts[i] = (x, y)
        self._commit(pts)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag = None

    def _commit(self, pts: list[tuple[float, float]]) -> None:
        self._curves.set_points(self._channel, pts)
        self.update()
        self.points_changed.emit(self._channel, list(self._curves.points[self._channel]))


class CurveEditor(QWidget):
    """Channel buttons + canvas + reset buttons.

    Signals:
        curve_changed(str, list): (channel, points) after any edit, live while dragging.
        channel_reset(str): A channel (or "all") was reset to the identity.
    """
    curve_changed = Signal(str, list)
    channel_reset = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.canvas = CurveCanvas(self)
        self.buttons: dict[str, QToolButton] = {}
        self.reset_button = QPushButton("Reset", self)
        self.reset_all_button = QPushButton("Reset all", self)
        self._group = QButtonGroup(self)
        self._build()

    def _build(self) -> None:
        row = QHBoxLayout()
        row.setSpacing(2)
        for channel in CHANNELS:
            button = QToolButton(self)
            button.setText(CHANNEL_LABELS[channel])
            button.setCheckable(True)
            button.setToolTip({"overall": "Overall curve, applied to every channel first",
                               "alpha": "Coverage curve: how much background shows through"}.get(channel, f"{channel.title()} curve"))
            color = CHANNEL_COLORS[channel]
            button.setStyleSheet(f"QToolButton:checked {{ background: {color.darker(160).name()}; color: white; }}")
            button.clicked.connect(lambda _checked=False, c=channel: self.select(c))
            self._group.addButton(button)
            self.buttons[channel] = button
            row.addWidget(button)
        row.addStretch(1)
        self.reset_button.setToolTip("Reset the selected channel to the identity")
        self.reset_all_button.setToolTip("Reset every channel")
        self.reset_button.clicked.connect(lambda: self._reset(self.canvas.channel()))
        self.reset_all_button.clicked.connect(lambda: self._reset(None))
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        bottom.addWidget(self.reset_button)
        bottom.addWidget(self.reset_all_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(row)
        layout.addWidget(self.canvas, 1)
        layout.addLayout(bottom)
        self.canvas.points_changed.connect(self.curve_changed)
        self.canvas.points_changed.connect(lambda *_: self._refresh_buttons())
        self.buttons["overall"].setChecked(True)

    # --- API ------------------------------------------------------------------------------------------------
    def set_curves(self, curves: Curves) -> None:
        """Show `curves` (no signal)."""
        self.canvas.set_curves(curves)
        self._refresh_buttons()

    def curves(self) -> Curves:
        return self.canvas.curves()

    def channel(self) -> str:
        return self.canvas.channel()

    def select(self, channel: str) -> None:
        self.canvas.set_channel(channel)
        self.buttons[channel].setChecked(True)

    def _reset(self, channel: str | None) -> None:
        curves = self.canvas.curves()
        curves.reset(channel)
        self.canvas.set_curves(curves)
        self._refresh_buttons()
        self.channel_reset.emit(channel or "all")

    def _refresh_buttons(self) -> None:
        curves = self.canvas.curves()
        for channel, button in self.buttons.items():
            button.setText(CHANNEL_LABELS[channel] + ("" if curves.is_default(channel) else " •"))


__all__ = ["CurveEditor", "CurveCanvas", "DEFAULT_POINTS"]
