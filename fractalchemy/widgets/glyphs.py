"""The painted glyphs of the Transform Editor, the Animation window and the Formula Editor: one small painter per name.

Every painter draws into a 16 × 16 design grid scaled by `u` (the size / 16), with the shared pen
already set. `glyph_pixmap(name, size)` looks the painter up in `GLYPHS`, so adding a glyph is one
function and one registry line, and an unknown name fails loudly instead of producing a blank icon.
"""

from __future__ import annotations

import math
from typing import Callable

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap

from .icons import GLYPH_ACCENT, GLYPH_COLOR, curved_arrow

Painter = Callable[[QPainter, float], None]
GREEN = QColor("#2e7d32")
RED = QColor("#c62828")
PAPER = QColor("#fafafa")
ACCENT_FILL = QColor(30, 136, 229, 60)


def _pen(color: QColor, width: float, style=Qt.PenStyle.SolidLine) -> QPen:
    return QPen(color, max(1.0, width), style, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)


def _accent(u: float) -> QPen:
    return _pen(GLYPH_ACCENT, 1.8 * u)


def _pts(u: float, *coords: tuple[float, float]) -> list[QPointF]:
    return [QPointF(x * u, y * u) for x, y in coords]


def _triangle(painter: QPainter, u: float, x: float, y: float, s: float, flip: bool = False) -> None:
    """A right triangle (X, O, Y corners like the editor's) with its origin corner at design point (x, y)."""
    sx = -1 if flip else 1
    painter.drawPolygon(_pts(u, (x + sx * s, y), (x, y), (x, y - s)))


def _film_strip(painter: QPainter, u: float, rect: QRectF, color: QColor) -> None:
    """A film-strip frame: a rounded rectangle with sprocket holes along the top and bottom."""
    painter.setPen(_pen(color, 1.2 * u))
    painter.setBrush(QColor(255, 255, 255, 40))
    painter.drawRoundedRect(rect, 1.2 * u, 1.2 * u)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    hole = 1.4 * u
    x = rect.left() + 1.2 * u
    while x + hole <= rect.right() - 0.8 * u:
        painter.drawRect(QRectF(x, rect.top() + 0.9 * u, hole, hole))
        painter.drawRect(QRectF(x, rect.bottom() - 0.9 * u - hole, hole, hole))
        x += hole + 1.3 * u


def _play_badge(painter: QPainter, u: float) -> None:
    """The green 'go' badge of the render glyphs."""
    painter.setBrush(QColor("#15803d"))
    painter.setPen(QPen(QColor(255, 255, 255), max(1.0, 0.8 * u)))
    painter.drawEllipse(QPointF(12 * u, 12 * u), 3.2 * u, 3.2 * u)
    painter.setBrush(QColor(255, 255, 255))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawPolygon(_pts(u, (10.9, 10.2), (10.9, 13.8), (14, 12)))


# --- editor glyphs ----------------------------------------------------------------------------------------------
def _editor(p: QPainter, u: float) -> None:
    p.setPen(_pen(GLYPH_ACCENT, 1.5 * u))
    p.setBrush(ACCENT_FILL)
    _triangle(p, u, 3.5, 13, 9.5)
    p.setBrush(PAPER)
    p.setPen(_pen(GLYPH_COLOR, u))
    for cx, cy in ((3.5, 13), (13, 13), (3.5, 3.5)):
        p.drawEllipse(QPointF(cx * u, cy * u), 1.6 * u, 1.6 * u)


def _add_transform(p: QPainter, u: float) -> None:
    _triangle(p, u, 3, 13, 8)
    p.setPen(_pen(GREEN, 2.0 * u))
    p.drawLine(*_pts(u, (11, 3), (11, 9)))
    p.drawLine(*_pts(u, (8, 6), (14, 6)))


def _duplicate_transform(p: QPainter, u: float) -> None:
    _triangle(p, u, 2.5, 10.5, 7)
    p.setPen(_accent(u))
    _triangle(p, u, 6.5, 14, 7)


def _delete_transform(p: QPainter, u: float) -> None:
    _triangle(p, u, 3, 13, 8)
    p.setPen(_pen(RED, 2.0 * u))
    p.drawLine(*_pts(u, (9, 3), (14, 8)))
    p.drawLine(*_pts(u, (14, 3), (9, 8)))


def _linked_transform(p: QPainter, u: float) -> None:
    _triangle(p, u, 2.5, 13, 6)
    p.setPen(_accent(u))
    _triangle(p, u, 9.5, 13, 5)
    p.drawLine(*_pts(u, (5, 6), (10.5, 6)))
    p.drawPolyline(_pts(u, (8.5, 4), (10.5, 6), (8.5, 8)))


def _final_transform(p: QPainter, u: float) -> None:
    _triangle(p, u, 2.5, 13.5, 10)
    p.setPen(_pen(GLYPH_ACCENT, 2.2 * u))
    p.drawLine(*_pts(u, (8, 5), (8, 13)))
    p.drawLine(*_pts(u, (8, 5), (13, 5)))
    p.drawLine(*_pts(u, (8, 9), (12, 9)))


def _select(p: QPainter, u: float) -> None:
    p.setBrush(PAPER)
    p.drawPolygon(_pts(u, (4, 2), (4, 13), (7, 10.5), (9, 14.5), (11, 13.5), (9, 9.5), (12.5, 9.5)))


def _move(p: QPainter, u: float) -> None:
    c = 8 * u
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        tip = QPointF(c + dx * 6 * u, c + dy * 6 * u)
        p.drawLine(QPointF(c, c), tip)
        p.drawLine(tip, QPointF(tip.x() - dx * 2.5 * u + dy * 2.0 * u, tip.y() - dy * 2.5 * u + dx * 2.0 * u))
        p.drawLine(tip, QPointF(tip.x() - dx * 2.5 * u - dy * 2.0 * u, tip.y() - dy * 2.5 * u - dx * 2.0 * u))


def _rotate(p: QPainter, u: float) -> None:
    rect = QRectF(3 * u, 3 * u, 10 * u, 10 * u)
    p.drawArc(rect, 30 * 16, 270 * 16)
    angle = math.radians(30)
    end = QPointF(rect.center().x() + rect.width() / 2 * math.cos(angle), rect.center().y() - rect.height() / 2 * math.sin(angle))
    p.setBrush(GLYPH_COLOR)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawPolygon([QPointF(end.x() + 2.4 * u, end.y() - 1.0 * u), QPointF(end.x() - 1.4 * u, end.y() - 2.6 * u),
                   QPointF(end.x() - 0.4 * u, end.y() + 2.2 * u)])


def _scale(p: QPainter, u: float) -> None:
    p.drawRect(QRectF(2.5 * u, 6.5 * u, 7 * u, 7 * u))
    p.setPen(_accent(u))
    p.drawLine(*_pts(u, (7, 9), (13.5, 2.5)))
    p.drawPolyline(_pts(u, (9.5, 2.5), (13.5, 2.5), (13.5, 6.5)))


def _pivot(p: QPainter, u: float) -> None:
    p.drawEllipse(QPointF(8 * u, 8 * u), 5 * u, 5 * u)
    p.drawLine(*_pts(u, (8, 1.5), (8, 14.5)))
    p.drawLine(*_pts(u, (1.5, 8), (14.5, 8)))
    p.setBrush(GLYPH_ACCENT)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QPointF(8 * u, 8 * u), 1.8 * u, 1.8 * u)


def _flip_h(p: QPainter, u: float) -> None:
    p.setBrush(ACCENT_FILL)
    p.setPen(_accent(u))
    _triangle(p, u, 7, 13, 5.5, flip=True)
    p.setPen(_pen(GLYPH_COLOR, 1.2 * u, Qt.PenStyle.DashLine))
    p.setBrush(Qt.BrushStyle.NoBrush)
    _triangle(p, u, 9, 13, 5.5)
    p.drawLine(*_pts(u, (8, 2), (8, 14.5)))


def _flip_v(p: QPainter, u: float) -> None:
    p.setBrush(ACCENT_FILL)
    p.setPen(_accent(u))
    p.drawPolygon(_pts(u, (3, 7), (8.5, 7), (3, 1.5)))
    p.setPen(_pen(GLYPH_COLOR, 1.2 * u, Qt.PenStyle.DashLine))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPolygon(_pts(u, (3, 9), (8.5, 9), (3, 14.5)))
    p.drawLine(*_pts(u, (1.5, 8), (14.5, 8)))


def _fit(p: QPainter, u: float) -> None:
    for (x, y, dx, dy) in ((2, 2, 1, 1), (14, 2, -1, 1), (2, 14, 1, -1), (14, 14, -1, -1)):
        p.drawLine(*_pts(u, (x, y), (x + dx * 4, y)))
        p.drawLine(*_pts(u, (x, y), (x, y + dy * 4)))
    p.setPen(_accent(u))
    _triangle(p, u, 5.5, 11, 5.5)


def _reload(p: QPainter, u: float) -> None:
    p.drawArc(QRectF(3 * u, 3 * u, 10 * u, 10 * u), 20 * 16, 300 * 16)
    p.setBrush(GLYPH_COLOR)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawPolygon(_pts(u, (13.5, 2.5), (13.5, 7), (9, 7)))


def _var_preview(p: QPainter, u: float) -> None:
    p.setPen(_pen(GLYPH_COLOR, 1.2 * u, Qt.PenStyle.DotLine))
    _triangle(p, u, 2.5, 13.5, 11)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(GLYPH_ACCENT)
    for cx, cy in ((5, 11), (8, 11), (11, 11), (5, 8), (8, 8), (5, 5), (9.5, 6.5), (12, 9), (7, 13.5)):
        p.drawEllipse(QPointF(cx * u, cy * u), 1.0 * u, 1.0 * u)


def _erase(p: QPainter, u: float) -> None:
    p.drawRect(QRectF(2.5 * u, 2.5 * u, 11 * u, 11 * u))
    p.setPen(_pen(GLYPH_COLOR, 1.2 * u, Qt.PenStyle.DotLine))
    _triangle(p, u, 5, 11, 6)


# --- animation glyphs -------------------------------------------------------------------------------------------
def _animation(p: QPainter, u: float) -> None:
    _film_strip(p, u, QRectF(1.5 * u, 3 * u, 13 * u, 10 * u), GLYPH_COLOR)
    p.setBrush(GLYPH_ACCENT)
    p.drawPolygon(_pts(u, (6.5, 5.8), (6.5, 10.2), (10.3, 8)))


def _film_with_badge(badge: QColor, draw_badge: Callable[[QPainter, float], None]) -> Painter:
    """A small film strip with a coloured mark in the top-right corner."""
    def painter(p: QPainter, u: float) -> None:
        _film_strip(p, u, QRectF(1.5 * u, 4.5 * u, 10 * u, 8 * u), GLYPH_COLOR)
        p.setPen(QPen(badge, max(1.0, 2.0 * u), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        draw_badge(p, u)
    return painter


def _plus(p: QPainter, u: float) -> None:
    p.drawLine(*_pts(u, (12, 2), (12, 7)))
    p.drawLine(*_pts(u, (9.5, 4.5), (14.5, 4.5)))


def _cross(p: QPainter, u: float) -> None:
    p.drawLine(*_pts(u, (10, 2.5), (14.5, 7)))
    p.drawLine(*_pts(u, (14.5, 2.5), (10, 7)))


def _refresh_arrow(p: QPainter, u: float) -> None:
    p.drawArc(QRectF(9.5 * u, 2 * u, 5 * u, 5 * u), 30 * 16, 280 * 16)
    p.setBrush(p.pen().color())
    p.setPen(Qt.PenStyle.NoPen)
    p.drawPolygon(_pts(u, (14.8, 3.2), (12.6, 2.0), (14.8, 0.8)))


def _solid(shape: Callable[[QPainter, float], None], color: QColor) -> Painter:
    """A filled shape without an outline."""
    def painter(p: QPainter, u: float) -> None:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        shape(p, u)
    return painter


def _play_shape(p: QPainter, u: float) -> None:
    p.drawPolygon(_pts(u, (4.5, 3), (4.5, 13), (13, 8)))


def _pause_shape(p: QPainter, u: float) -> None:
    p.drawRect(QRectF(4 * u, 3 * u, 3 * u, 10 * u))
    p.drawRect(QRectF(9 * u, 3 * u, 3 * u, 10 * u))


def _stop_shape(p: QPainter, u: float) -> None:
    p.drawRect(QRectF(4 * u, 4 * u, 8 * u, 8 * u))


def _transport(shape: Callable[[QPainter, float], None], flip: bool) -> Painter:
    """A transport glyph drawn about the centre, mirrored for the 'previous' / 'first' variants."""
    def painter(p: QPainter, u: float) -> None:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(GLYPH_COLOR)
        p.translate(8 * u, 8 * u)
        if flip:
            p.scale(-1, 1)
        shape(p, u)
    return painter


def _skip_shape(p: QPainter, u: float) -> None:
    p.drawPolygon(_pts(u, (-5.5, -5), (-5.5, 5), (2.5, 0)))
    p.drawRect(QRectF(3 * u, -5 * u, 2 * u, 10 * u))


def _keyframe_shape(p: QPainter, u: float) -> None:
    """An arrow into a diamond (the timeline's keyframe marker)."""
    p.drawPolygon(_pts(u, (-6.5, -4), (-6.5, 4), (0, 0)))
    p.setBrush(GLYPH_ACCENT)
    p.drawPolygon(_pts(u, (3.5, -4), (7, 0), (3.5, 4), (0, 0)))


def _anim_render(p: QPainter, u: float) -> None:
    _film_strip(p, u, QRectF(1.5 * u, 3 * u, 13 * u, 10 * u), GLYPH_COLOR)
    _play_badge(p, u)


# --- formula editor glyphs --------------------------------------------------------------------------------------
def _formula_text(p: QPainter, u: float, text: str, rect: QRectF, color: QColor, size: float, italic: bool = True) -> None:
    """Serif, italic lettering — the algebra look of the Formula Editor's glyphs."""
    font = QFont("serif")
    font.setItalic(italic)
    font.setBold(True)
    font.setPixelSize(max(6, int(size * u)))
    p.setFont(font)
    p.setPen(_pen(color, u))
    p.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)


def _formula_editor(p: QPainter, u: float) -> None:
    """A sheet with a big italic ƒ and a small v (the variation) — the Formula Editor's window and toolbar glyph."""
    p.setPen(_pen(QColor(60, 60, 60), 0.9 * u))
    p.setBrush(PAPER)
    p.drawRoundedRect(QRectF(2 * u, 1.5 * u, 12 * u, 13 * u), u, u)
    _formula_text(p, u, "ƒ", QRectF(2.5 * u, 1.0 * u, 8 * u, 13 * u), GLYPH_ACCENT, 12.5)
    _formula_text(p, u, "v", QRectF(8.5 * u, 7.5 * u, 5.5 * u, 6.5 * u), GLYPH_COLOR, 7)


def _add_linear(p: QPainter, u: float) -> None:
    """A triangle with a straight arrow: add a linear transform."""
    _triangle(p, u, 3, 13, 8)
    p.setPen(_pen(GREEN, 1.8 * u))
    p.drawLine(*_pts(u, (8.5, 5.5), (14, 5.5)))
    p.drawPolyline(_pts(u, (11.5, 3), (14, 5.5), (11.5, 8)))


def _add_spherical(p: QPainter, u: float) -> None:
    """A triangle with a small circle: add a spherical transform."""
    _triangle(p, u, 3, 13, 8)
    p.setPen(_pen(GREEN, 1.8 * u))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QPointF(11.5 * u, 5.5 * u), 2.8 * u, 2.8 * u)


def _add_formula(p: QPainter, u: float) -> None:
    """A triangle with a ƒ: add a transform running the formula being edited."""
    _triangle(p, u, 3, 13, 8)
    _formula_text(p, u, "ƒ", QRectF(8 * u, 0.5 * u, 7.5 * u, 10 * u), GLYPH_ACCENT, 10)


def _use_formula(p: QPainter, u: float) -> None:
    """A ƒ inside a filled triangle: put the formula on the selected transform."""
    p.setPen(_pen(GLYPH_ACCENT, 1.5 * u))
    p.setBrush(ACCENT_FILL)
    _triangle(p, u, 2.5, 13.5, 11)
    _formula_text(p, u, "ƒ", QRectF(2.5 * u, 5 * u, 7 * u, 9 * u), GLYPH_ACCENT, 8)


def _new_formula(p: QPainter, u: float) -> None:
    """A blank sheet with a green plus: a new formula from the template."""
    p.setBrush(PAPER)
    p.drawPolygon(_pts(u, (3, 2), (9.5, 2), (13, 5.5), (13, 14), (3, 14)))
    p.drawPolyline(_pts(u, (9.5, 2), (9.5, 5.5), (13, 5.5)))
    p.setPen(_pen(GREEN, 2.0 * u))
    p.drawLine(*_pts(u, (8, 7.5), (8, 12.5)))
    p.drawLine(*_pts(u, (5.5, 10), (10.5, 10)))


def _add_variable(p: QPainter, u: float) -> None:
    """An italic x with a green plus: declare a variable."""
    _formula_text(p, u, "x", QRectF(1.5 * u, 2 * u, 8 * u, 12 * u), GLYPH_COLOR, 11)
    p.setPen(_pen(GREEN, 2.0 * u))
    p.drawLine(*_pts(u, (12, 2.5), (12, 8.5)))
    p.drawLine(*_pts(u, (9, 5.5), (15, 5.5)))


def _compare(p: QPainter, u: float) -> None:
    """Two framed panes side by side, the right one in the accent colour: compare with the original."""
    p.setBrush(PAPER)
    p.drawRect(QRectF(1.5 * u, 3.5 * u, 6 * u, 9 * u))
    p.setPen(_pen(GLYPH_ACCENT, 1.5 * u))
    p.setBrush(ACCENT_FILL)
    p.drawRect(QRectF(8.5 * u, 3.5 * u, 6 * u, 9 * u))


GLYPHS: dict[str, Painter] = {
    "editor": _editor, "add-transform": _add_transform, "duplicate-transform": _duplicate_transform,
    "delete-transform": _delete_transform, "linked-transform": _linked_transform, "final-transform": _final_transform,
    "select": _select, "move": _move, "rotate": _rotate, "scale": _scale, "pivot": _pivot,
    "rotate-ccw": lambda p, u: curved_arrow(p, u, mirrored=False), "rotate-cw": lambda p, u: curved_arrow(p, u, mirrored=True),
    "flip-h": _flip_h, "flip-v": _flip_v, "fit": _fit, "reload": _reload, "var-preview": _var_preview, "erase": _erase,
    "animation": _animation,
    "anim-new": _film_with_badge(PAPER, lambda p, u: None), "anim-capture": _film_with_badge(GREEN, _plus),
    "anim-update": _film_with_badge(GLYPH_ACCENT, _refresh_arrow), "anim-delete": _film_with_badge(RED, _cross),
    "anim-play": _solid(_play_shape, GLYPH_ACCENT), "anim-pause": _solid(_pause_shape, GLYPH_COLOR), "anim-stop": _solid(_stop_shape, GLYPH_COLOR),
    "anim-first": _transport(_skip_shape, flip=True), "anim-last": _transport(_skip_shape, flip=False),
    "anim-prev": _transport(_keyframe_shape, flip=True), "anim-next": _transport(_keyframe_shape, flip=False),
    "anim-render": _anim_render,
    "formula-editor": _formula_editor, "add-linear": _add_linear, "add-spherical": _add_spherical, "add-formula": _add_formula,
    "use-formula": _use_formula, "new-formula": _new_formula, "add-variable": _add_variable, "compare": _compare,
}


def glyph_pixmap(name: str, size: int) -> QPixmap:
    """Paint the glyph called `name` at `size` pixels.

    Raises:
        KeyError: For an unregistered name.
    """
    if name not in GLYPHS:
        raise KeyError(f"no glyph called {name!r} (known: {', '.join(sorted(GLYPHS))})")
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    u = size / 16.0
    painter.setPen(_pen(GLYPH_COLOR, 1.5 * u))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    GLYPHS[name](painter, u)
    painter.end()
    return pixmap


__all__ = ["GLYPHS", "glyph_pixmap"]
