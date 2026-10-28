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
        curved_arrow(painter, u, mirrored=name == "redo")
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


def curved_arrow(painter: QPainter, u: float, mirrored: bool) -> None:
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


# --- the Transform Editor's and the Animation window's glyphs (painters in `glyphs.py`) ----------------------
EDITOR_THEME_NAMES = {
    "add-transform": "list-add", "delete-transform": "edit-delete", "duplicate-transform": "edit-copy",
    "select": "edit-select", "move": "transform-move", "rotate": "transform-rotate", "scale": "transform-scale",
    "rotate-ccw": "object-rotate-left", "rotate-cw": "object-rotate-right", "flip-h": "object-flip-horizontal",
    "flip-v": "object-flip-vertical", "fit": "zoom-fit-best", "reload": "view-refresh",
}


def editor_icon(name: str, use_theme: bool = False) -> QIcon:
    """A glyph for one of the editor / animation actions (painted; the platform theme's icon if `use_theme`).

    Raises:
        KeyError: For a name no glyph is registered under (see `glyphs.GLYPHS`).
    """
    from .glyphs import glyph_pixmap
    if use_theme:
        themed = QIcon.fromTheme(EDITOR_THEME_NAMES.get(name, ""))
        if not themed.isNull():
            return themed
    icon = QIcon()
    for size in ICON_SIZES:
        icon.addPixmap(glyph_pixmap(name, size))
    return icon


def animation_icon() -> QIcon:
    """A film strip — the Animation window / toolbar glyph."""
    return editor_icon("animation")
