"""Icons painted at run time, so no image resources need shipping.

    action.setIcon(gradient_icon())

Each icon is rendered at several sizes so toolbars and title bars stay crisp on
high-DPI screens.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPen, QPixmap

from .. import config

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


# --- the standard editing glyphs -----------------------------------------------------------------------------
THEME_NAMES = {"undo": "edit-undo", "redo": "edit-redo", "copy": "edit-copy", "paste": "edit-paste", "save": "document-save",
               "save-as": "document-save-as", "random": "roll"}
GLYPH_COLOR = QColor("#3b3b3b")
GLYPH_ACCENT = QColor(config.HIGHLIGHT_COLOR)


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
    """The platform theme's icon for undo / redo / copy / paste / save, or our painted look-alike."""
    themed = QIcon.fromTheme(THEME_NAMES.get(name, name))
    if not themed.isNull():
        return themed
    icon = QIcon()
    for size in ICON_SIZES:
        icon.addPixmap(_glyph_pixmap(name, size))
    return icon


def _glyph_pixmap(name: str, size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    u = size / 16.0
    pen = QPen(GLYPH_COLOR, max(1.0, 1.6 * u), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    if name in ("undo", "redo"):
        _curved_arrow(painter, u, mirrored=name == "redo")
    elif name == "copy":
        painter.setBrush(QColor("#fafafa"))
        painter.drawRoundedRect(QRectF(2 * u, 2 * u, 8 * u, 9.5 * u), u, u)
        painter.drawRoundedRect(QRectF(6 * u, 5 * u, 8 * u, 9.5 * u), u, u)
    elif name == "paste":
        painter.setBrush(QColor("#c9a36b"))
        painter.drawRoundedRect(QRectF(2.5 * u, 3 * u, 11 * u, 11.5 * u), u, u)      # the clipboard
        painter.setBrush(GLYPH_COLOR)
        painter.drawRoundedRect(QRectF(5.5 * u, 1.5 * u, 5 * u, 3 * u), 0.8 * u, 0.8 * u)   # its clip
        painter.setBrush(QColor("#fafafa"))
        painter.drawRect(QRectF(4.5 * u, 6 * u, 7 * u, 7 * u))                          # the sheet
    elif name in ("save", "save-as"):
        painter.setBrush(GLYPH_ACCENT)
        painter.drawRoundedRect(QRectF(2 * u, 2 * u, 12 * u, 12 * u), u, u)             # the diskette
        painter.setBrush(QColor("#fafafa"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(QRectF(4.5 * u, 2.5 * u, 7 * u, 4 * u))
        painter.drawRect(QRectF(4 * u, 9 * u, 8 * u, 5 * u))
        if name == "save-as":
            _pencil(painter, u)
    elif name == "random":
        painter.setBrush(QColor("#fafafa"))
        painter.drawRoundedRect(QRectF(2 * u, 2 * u, 12 * u, 12 * u), 2 * u, 2 * u)     # a die
        painter.setBrush(GLYPH_COLOR)
        painter.setPen(Qt.PenStyle.NoPen)
        for cx, cy in ((5, 5), (11, 5), (8, 8), (5, 11), (11, 11)):
            painter.drawEllipse(QPointF(cx * u, cy * u), 1.3 * u, 1.3 * u)
    painter.end()
    return pixmap


def _pencil(painter: QPainter, u: float) -> None:
    """A small pencil over the bottom-right corner (the 'save as' marker), outlined in white for contrast."""
    painter.save()
    painter.translate(11.2 * u, 11.2 * u)
    painter.rotate(-45)
    body = QRectF(-1.6 * u, -5.2 * u, 3.2 * u, 7.4 * u)
    painter.setPen(QPen(QColor("#ffffff"), max(1.0, 1.2 * u)))
    painter.setBrush(QColor("#f4b400"))
    painter.drawRect(body)
    tip = [QPointF(-1.6 * u, 2.2 * u), QPointF(1.6 * u, 2.2 * u), QPointF(0.0, 4.6 * u)]
    painter.setBrush(QColor("#f8e0b0"))
    painter.drawPolygon(tip)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#e57373"))
    painter.drawRect(QRectF(-1.6 * u, -5.2 * u, 3.2 * u, 1.6 * u))   # the eraser end
    painter.setBrush(GLYPH_COLOR)
    painter.drawPolygon([QPointF(-0.6 * u, 3.7 * u), QPointF(0.6 * u, 3.7 * u), QPointF(0.0, 4.6 * u)])   # the lead
    painter.restore()


def _curved_arrow(painter: QPainter, u: float, mirrored: bool) -> None:
    """An undo-style arrow: an arc from the right over the top to the left, ending in a head that points down
    (mirrored for redo)."""
    import math
    if mirrored:
        painter.translate(16 * u, 0)
        painter.scale(-1, 1)
    rect = QRectF(3.5 * u, 3.5 * u, 9 * u, 9 * u)
    painter.drawArc(rect, 0, 200 * 16)
    angle = math.radians(200)
    end = QPointF(rect.center().x() + rect.width() / 2 * math.cos(angle), rect.center().y() - rect.height() / 2 * math.sin(angle))
    painter.setBrush(painter.pen().color())
    head = [QPointF(end.x(), end.y() + 2.6 * u), QPointF(end.x() - 2.4 * u, end.y() - 1.2 * u), QPointF(end.x() + 2.6 * u, end.y() - 1.2 * u)]
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawPolygon(head)


# --- the Transform Editor's glyphs -------------------------------------------------------------------------
EDITOR_THEME_NAMES = {
    "add-transform": "list-add", "delete-transform": "edit-delete", "duplicate-transform": "edit-copy",
    "select": "edit-select", "move": "transform-move", "rotate": "transform-rotate", "scale": "transform-scale",
    "rotate-ccw": "object-rotate-left", "rotate-cw": "object-rotate-right", "flip-h": "object-flip-horizontal",
    "flip-v": "object-flip-vertical", "fit": "zoom-fit-best", "reload": "view-refresh",
}


def editor_icon(name: str, use_theme: bool = False) -> QIcon:
    """A glyph for one of the Transform Editor's actions (painted; the platform theme's icon if `use_theme`)."""
    if use_theme:
        themed = QIcon.fromTheme(EDITOR_THEME_NAMES.get(name, ""))
        if not themed.isNull():
            return themed
    icon = QIcon()
    for size in ICON_SIZES:
        icon.addPixmap(_editor_pixmap(name, size))
    return icon


def _triangle(painter: QPainter, u: float, x: float, y: float, s: float, flip: bool = False) -> None:
    """A right triangle (X, O, Y corners like the editor's) with its origin corner at (x, y)."""
    sx = -1 if flip else 1
    painter.drawPolygon([QPointF(x + sx * s * u, y), QPointF(x, y), QPointF(x, y - s * u)])


def _editor_pixmap(name: str, size: int) -> QPixmap:
    import math
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    u = size / 16.0
    pen = QPen(GLYPH_COLOR, max(1.0, 1.5 * u), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    accent = QPen(GLYPH_ACCENT, max(1.0, 1.8 * u), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    if name == "editor":
        painter.setPen(QPen(GLYPH_ACCENT, max(1.0, 1.5 * u)))
        painter.setBrush(QColor(30, 136, 229, 60))
        _triangle(painter, u, 3.5, 13, 9.5)
        painter.setBrush(QColor("#fafafa"))
        painter.setPen(QPen(GLYPH_COLOR, max(1.0, u)))
        for cx, cy in ((3.5, 13), (13, 13), (3.5, 3.5)):
            painter.drawEllipse(QPointF(cx * u, cy * u), 1.6 * u, 1.6 * u)
    elif name == "add-transform":
        _triangle(painter, u, 3, 13, 8)
        painter.setPen(QPen(QColor("#2e7d32"), max(1.0, 2.0 * u), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(11 * u, 3 * u), QPointF(11 * u, 9 * u))
        painter.drawLine(QPointF(8 * u, 6 * u), QPointF(14 * u, 6 * u))
    elif name == "duplicate-transform":
        _triangle(painter, u, 2.5, 10.5, 7)
        painter.setPen(accent)
        _triangle(painter, u, 6.5, 14, 7)
    elif name == "delete-transform":
        _triangle(painter, u, 3, 13, 8)
        painter.setPen(QPen(QColor("#c62828"), max(1.0, 2.0 * u), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(9 * u, 3 * u), QPointF(14 * u, 8 * u))
        painter.drawLine(QPointF(14 * u, 3 * u), QPointF(9 * u, 8 * u))
    elif name == "linked-transform":
        _triangle(painter, u, 2.5, 13, 6)
        painter.setPen(accent)
        _triangle(painter, u, 9.5, 13, 5)
        painter.drawLine(QPointF(5 * u, 6 * u), QPointF(10.5 * u, 6 * u))
        painter.drawPolyline([QPointF(8.5 * u, 4 * u), QPointF(10.5 * u, 6 * u), QPointF(8.5 * u, 8 * u)])
    elif name == "final-transform":
        painter.setPen(QPen(GLYPH_COLOR, max(1.0, 1.5 * u)))
        _triangle(painter, u, 2.5, 13.5, 10)
        painter.setPen(QPen(GLYPH_ACCENT, max(1.0, 2.2 * u), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(8 * u, 5 * u), QPointF(8 * u, 13 * u))
        painter.drawLine(QPointF(8 * u, 5 * u), QPointF(13 * u, 5 * u))
        painter.drawLine(QPointF(8 * u, 9 * u), QPointF(12 * u, 9 * u))
    elif name == "select":
        painter.setBrush(QColor("#fafafa"))
        painter.drawPolygon([QPointF(4 * u, 2 * u), QPointF(4 * u, 13 * u), QPointF(7 * u, 10.5 * u), QPointF(9 * u, 14.5 * u),
                             QPointF(11 * u, 13.5 * u), QPointF(9 * u, 9.5 * u), QPointF(12.5 * u, 9.5 * u)])
    elif name == "move":
        c = 8 * u
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            tip = QPointF(c + dx * 6 * u, c + dy * 6 * u)
            painter.drawLine(QPointF(c, c), tip)
            painter.drawLine(tip, QPointF(tip.x() - dx * 2.5 * u + dy * 2.0 * u, tip.y() - dy * 2.5 * u + dx * 2.0 * u))
            painter.drawLine(tip, QPointF(tip.x() - dx * 2.5 * u - dy * 2.0 * u, tip.y() - dy * 2.5 * u - dx * 2.0 * u))
    elif name == "rotate":
        rect = QRectF(3 * u, 3 * u, 10 * u, 10 * u)
        painter.drawArc(rect, 30 * 16, 270 * 16)
        angle = math.radians(30)
        end = QPointF(rect.center().x() + rect.width() / 2 * math.cos(angle), rect.center().y() - rect.height() / 2 * math.sin(angle))
        painter.setBrush(GLYPH_COLOR)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon([QPointF(end.x() + 2.4 * u, end.y() - 1.0 * u), QPointF(end.x() - 1.4 * u, end.y() - 2.6 * u),
                             QPointF(end.x() - 0.4 * u, end.y() + 2.2 * u)])
    elif name == "scale":
        painter.drawRect(QRectF(2.5 * u, 6.5 * u, 7 * u, 7 * u))
        painter.setPen(accent)
        painter.drawLine(QPointF(7 * u, 9 * u), QPointF(13.5 * u, 2.5 * u))
        painter.drawPolyline([QPointF(9.5 * u, 2.5 * u), QPointF(13.5 * u, 2.5 * u), QPointF(13.5 * u, 6.5 * u)])
    elif name == "pivot":
        painter.drawEllipse(QPointF(8 * u, 8 * u), 5 * u, 5 * u)
        painter.drawLine(QPointF(8 * u, 1.5 * u), QPointF(8 * u, 14.5 * u))
        painter.drawLine(QPointF(1.5 * u, 8 * u), QPointF(14.5 * u, 8 * u))
        painter.setBrush(GLYPH_ACCENT)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(8 * u, 8 * u), 1.8 * u, 1.8 * u)
    elif name in ("rotate-ccw", "rotate-cw"):
        _curved_arrow(painter, u, mirrored=name == "rotate-cw")
    elif name == "flip-h":
        painter.setBrush(QColor(30, 136, 229, 60))
        painter.setPen(accent)
        _triangle(painter, u, 7, 13, 5.5, flip=True)
        painter.setPen(QPen(GLYPH_COLOR, max(1.0, 1.2 * u), Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        _triangle(painter, u, 9, 13, 5.5)
        painter.drawLine(QPointF(8 * u, 2 * u), QPointF(8 * u, 14.5 * u))
    elif name == "flip-v":
        painter.setBrush(QColor(30, 136, 229, 60))
        painter.setPen(accent)
        painter.drawPolygon([QPointF(3 * u, 7 * u), QPointF(8.5 * u, 7 * u), QPointF(3 * u, 1.5 * u)])
        painter.setPen(QPen(GLYPH_COLOR, max(1.0, 1.2 * u), Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolygon([QPointF(3 * u, 9 * u), QPointF(8.5 * u, 9 * u), QPointF(3 * u, 14.5 * u)])
        painter.drawLine(QPointF(1.5 * u, 8 * u), QPointF(14.5 * u, 8 * u))
    elif name == "fit":
        for (x, y, dx, dy) in ((2, 2, 1, 1), (14, 2, -1, 1), (2, 14, 1, -1), (14, 14, -1, -1)):
            painter.drawLine(QPointF(x * u, y * u), QPointF((x + dx * 4) * u, y * u))
            painter.drawLine(QPointF(x * u, y * u), QPointF(x * u, (y + dy * 4) * u))
        painter.setPen(accent)
        _triangle(painter, u, 5.5, 11, 5.5)
    elif name == "reload":
        rect = QRectF(3 * u, 3 * u, 10 * u, 10 * u)
        painter.drawArc(rect, 20 * 16, 300 * 16)
        painter.setBrush(GLYPH_COLOR)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon([QPointF(13.5 * u, 2.5 * u), QPointF(13.5 * u, 7 * u), QPointF(9 * u, 7 * u)])
    elif name == "var-preview":
        painter.setPen(QPen(GLYPH_COLOR, max(1.0, 1.2 * u), Qt.PenStyle.DotLine))
        _triangle(painter, u, 2.5, 13.5, 11)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(GLYPH_ACCENT)
        for cx, cy in ((5, 11), (8, 11), (11, 11), (5, 8), (8, 8), (5, 5), (9.5, 6.5), (12, 9), (7, 13.5)):
            painter.drawEllipse(QPointF(cx * u, cy * u), 1.0 * u, 1.0 * u)
    elif name == "erase":
        painter.drawRect(QRectF(2.5 * u, 2.5 * u, 11 * u, 11 * u))
        painter.setPen(QPen(GLYPH_COLOR, max(1.0, 1.2 * u), Qt.PenStyle.DotLine))
        _triangle(painter, u, 5, 11, 6)
    painter.end()
    return pixmap
