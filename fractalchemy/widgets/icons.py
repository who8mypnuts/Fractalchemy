"""Icons painted at run time, so no image resources need shipping.

    action.setIcon(gradient_icon())

Each icon is rendered at several sizes so toolbars and title bars stay crisp on
high-DPI screens.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPen, QPixmap

ICON_SIZES = (16, 24, 32, 48, 64)
RAINBOW = ((0.0, "#e53935"), (0.2, "#ffb300"), (0.4, "#43a047"), (0.6, "#1e88e5"), (0.8, "#8e24aa"), (1.0, "#e53935"))
NODE_POSITIONS = (0.15, 0.5, 0.85)


def gradient_icon() -> QIcon:
    """A colour bar with three nodes beneath it — the Gradient Library glyph."""
    icon = QIcon()
    for size in ICON_SIZES:
        icon.addPixmap(_gradient_pixmap(size))
    return icon


def _gradient_pixmap(size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    unit = size / 16.0
    bar = QRectF(unit, 3 * unit, size - 2 * unit, 7 * unit)
    fill = QLinearGradient(bar.topLeft(), bar.topRight())
    for position, colour in RAINBOW:
        fill.setColorAt(position, QColor(colour))
    painter.setBrush(fill)
    painter.setPen(QPen(QColor(0, 0, 0, 170), max(1.0, unit * 0.6)))
    painter.drawRoundedRect(bar, unit, unit)
    painter.setBrush(QColor("#f5f5f5"))
    radius = max(1.2, 1.4 * unit)
    y = bar.bottom() + 2.2 * unit
    for fraction in NODE_POSITIONS:
        painter.drawEllipse(QPointF(bar.left() + fraction * bar.width(), y), radius, radius)
    painter.end()
    return pixmap


def render_icon() -> QIcon:
    """A framed picture (sun over hills) with a green 'go' badge — the Render Image glyph."""
    icon = QIcon()
    for size in ICON_SIZES:
        icon.addPixmap(_render_pixmap(size))
    return icon


def _render_pixmap(size: int) -> QPixmap:
    from PySide6.QtGui import QPolygonF

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    u = size / 16.0
    frame = QRectF(1.5 * u, 2 * u, 13 * u, 11 * u)
    sky = QLinearGradient(frame.topLeft(), frame.bottomLeft())
    sky.setColorAt(0.0, QColor("#1e3a8a"))
    sky.setColorAt(1.0, QColor("#60a5fa"))
    painter.setBrush(sky)
    painter.setPen(QPen(QColor(40, 40, 40), max(1.0, 0.9 * u)))
    painter.drawRoundedRect(frame, u, u)
    painter.setClipRect(frame.adjusted(0.5 * u, 0.5 * u, -0.5 * u, -0.5 * u))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#fbbf24"))
    painter.drawEllipse(QPointF(5 * u, 5.5 * u), 1.8 * u, 1.8 * u)
    painter.setBrush(QColor("#166534"))
    painter.drawPolygon(QPolygonF([QPointF(1.5 * u, 13 * u), QPointF(6 * u, 7.5 * u), QPointF(10 * u, 13 * u)]))
    painter.setBrush(QColor("#22c55e"))
    painter.drawPolygon(QPolygonF([QPointF(7 * u, 13 * u), QPointF(11 * u, 8.5 * u), QPointF(15 * u, 13 * u)]))
    painter.setClipping(False)
    badge = QPointF(12 * u, 12 * u)
    painter.setBrush(QColor("#15803d"))
    painter.setPen(QPen(QColor(255, 255, 255), max(1.0, 0.8 * u)))
    painter.drawEllipse(badge, 3.2 * u, 3.2 * u)
    painter.setBrush(QColor(255, 255, 255))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawPolygon(QPolygonF([QPointF(10.9 * u, 10.2 * u), QPointF(10.9 * u, 13.8 * u), QPointF(14 * u, 12 * u)]))
    painter.end()
    return pixmap


def link_icon(linked: bool) -> QIcon:
    """Two chain links: joined and bold blue when the aspect ratio is locked, broken and faint when free.

    The colours carry the state on their own, because a checked tool button's highlight differs
    between platform styles (and can swallow a plain dark glyph).
    """
    icon = QIcon()
    for size in ICON_SIZES:
        icon.addPixmap(_link_pixmap(size, linked))
    return icon


def _link_pixmap(size: int, linked: bool) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    u = size / 16.0
    pen = QPen(QColor("#1e6fd9") if linked else QColor(165, 165, 165), max(1.0, (2.0 if linked else 1.4) * u))
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    gap = 0.0 if linked else 1.6 * u
    painter.drawRoundedRect(QRectF(3 * u, 2 * u - gap, 5 * u, 7 * u), 2.5 * u, 2.5 * u)
    painter.drawRoundedRect(QRectF(8 * u, 7 * u + gap, 5 * u, 7 * u), 2.5 * u, 2.5 * u)
    if linked:
        painter.drawLine(QPointF(6.5 * u, 5 * u), QPointF(9.5 * u, 11 * u))
    else:
        painter.setPen(QPen(QColor(200, 70, 70), max(1.0, 1.4 * u)))
        painter.drawLine(QPointF(6.5 * u, 6.5 * u), QPointF(9.5 * u, 9.5 * u))   # the cut
    painter.end()
    return pixmap


# --- standard actions: theme icon when the platform has one, else a painted glyph -------------------
def action_icon(name: str) -> QIcon:
    """Icon for 'undo', 'redo', 'copy', 'paste', 'save', 'save-as', 'open'."""
    themed = QIcon.fromTheme(_THEME_NAMES.get(name, name))
    if not themed.isNull():
        return themed
    icon = QIcon()
    for size in ICON_SIZES:
        icon.addPixmap(_glyph_pixmap(name, size))
    return icon


_THEME_NAMES = {"undo": "edit-undo", "redo": "edit-redo", "copy": "edit-copy", "paste": "edit-paste",
                "save": "document-save", "save-as": "document-save-as", "open": "document-open"}


def _glyph_pixmap(name: str, size: int) -> QPixmap:
    from PySide6.QtCore import QRectF as _QRectF
    from PySide6.QtGui import QPainterPath, QPolygonF

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    u = size / 16.0
    ink = QColor(60, 60, 60)
    pen = QPen(ink, max(1.0, 1.6 * u))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    if name in ("undo", "redo"):
        if name == "redo":
            painter.translate(size, 0)
            painter.scale(-1, 1)
        path = QPainterPath(QPointF(4 * u, 6 * u))
        path.cubicTo(QPointF(9 * u, 4 * u), QPointF(13 * u, 7 * u), QPointF(12 * u, 12 * u))
        painter.drawPath(path)
        painter.setBrush(ink)
        painter.drawPolygon(QPolygonF([QPointF(2 * u, 6 * u), QPointF(6.5 * u, 3 * u), QPointF(6.5 * u, 9 * u)]))
    elif name == "copy":
        painter.drawRect(_QRectF(3 * u, 2 * u, 7 * u, 8.5 * u))
        painter.setBrush(QColor(245, 245, 245))
        painter.drawRect(_QRectF(6 * u, 5.5 * u, 7 * u, 8.5 * u))
    elif name == "paste":
        painter.setBrush(QColor(245, 245, 245))
        painter.drawRoundedRect(_QRectF(3 * u, 3 * u, 10 * u, 11 * u), u, u)
        painter.setBrush(ink)
        painter.drawRect(_QRectF(6 * u, 1.5 * u, 4 * u, 3 * u))
        painter.setPen(QPen(ink, max(1.0, 1.2 * u)))
        for y in (7.5, 10, 12):
            painter.drawLine(QPointF(5 * u, y * u), QPointF(11 * u, y * u))
    elif name in ("save", "save-as"):
        painter.setBrush(QColor(245, 245, 245))
        painter.drawRoundedRect(_QRectF(2 * u, 2 * u, 12 * u, 12 * u), u, u)
        painter.setBrush(ink)
        painter.drawRect(_QRectF(5 * u, 2 * u, 6 * u, 4 * u))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(_QRectF(4.5 * u, 9 * u, 7 * u, 5 * u))
        if name == "save-as":
            painter.setPen(QPen(QColor(200, 60, 60), max(1.0, 1.6 * u)))
            painter.drawLine(QPointF(10 * u, 10 * u), QPointF(14 * u, 14 * u))
            painter.drawLine(QPointF(14 * u, 10 * u), QPointF(10 * u, 14 * u))
    elif name == "open":
        painter.setBrush(QColor(240, 200, 90))
        painter.drawRoundedRect(_QRectF(2 * u, 4 * u, 12 * u, 9 * u), u, u)
        painter.drawRect(_QRectF(2 * u, 3 * u, 5 * u, 3 * u))
    painter.end()
    return pixmap
