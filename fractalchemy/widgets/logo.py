"""The proposed Fractalchemy mark: an alchemist's flask whose contents are a fractal spiral.

The flask is the alchemical sign for fire (a triangle) with a neck — one bold, rounded stroke that stays
crisp at 16 px — and inside it a logarithmic spiral of circles that shrink by the golden ratio (the
self-similarity of a fractal) coloured by the app's flame gradient, ember orange through magenta to the
accent blue. Two bubbles rise in the neck. `logo_pixmap(size)` paints it at any size; `logo_icon()` is the
multi-size QIcon for windows and the task bar; `wordmark_pixmap()` sets the mark beside the name. `VARIANTS`
lists the alternatives (single colour, squares, round-bottom flask, triangle bubbles); `tools/render_logo.py`
renders them all at high resolution into `logo/`.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF

INK = QColor("#1f2a44")                 # the flask: deep indigo
FLAME = ((0.0, "#ffb347"), (0.35, "#ff6a00"), (0.7, "#e6007e"), (1.0, "#1e88e5"))
BUBBLE = QColor("#1e88e5")
GOLDEN = (1 + 5 ** 0.5) / 2
SIZES = (16, 24, 32, 48, 64, 128, 256)
MAIN, MONO, SQUARES, ROUND, TRIANGLES = "main", "mono", "squares", "round", "triangles"
VARIANTS = {
    MAIN: "the mark: an Erlenmeyer flask with a golden-ratio spiral of circles in the flame colours",
    MONO: "single colour — for print, stamps and monochrome contexts",
    SQUARES: "the spiral made of squares, a Sierpinski feel",
    ROUND: "a round-bottom flask",
    TRIANGLES: "the bubbles as tiny triangles echoing the fire sign",
}


def _flask_path(u: float, round_bottom: bool = False) -> QPainterPath:
    """The flask outline on a 64-unit grid, scaled by `u`: lip, neck, flaring body, rounded bottom."""
    p = QPainterPath()
    p.moveTo(24 * u, 7 * u)
    p.lineTo(40 * u, 7 * u)                    # the lip
    p.moveTo(27 * u, 7 * u)
    p.lineTo(27 * u, 22 * u)                   # the neck
    if round_bottom:
        p.arcTo(QRectF(10 * u, 20 * u, 44 * u, 36 * u), 125, 290)
        p.lineTo(37 * u, 22 * u)
    else:
        p.lineTo(8.5 * u, 50 * u)              # the body flares out
        p.quadTo(6 * u, 56 * u, 12 * u, 56 * u)    # rounded bottom-left
        p.lineTo(52 * u, 56 * u)
        p.quadTo(58 * u, 56 * u, 55.5 * u, 50 * u)  # rounded bottom-right
        p.lineTo(37 * u, 22 * u)
    p.lineTo(37 * u, 7 * u)
    return p


def _body_path(u: float, round_bottom: bool = False) -> QPainterPath:
    """The closed body, for the glass tint and for clipping the spiral."""
    p = QPainterPath()
    p.moveTo(27 * u, 22 * u)
    if round_bottom:
        p.arcTo(QRectF(10 * u, 20 * u, 44 * u, 36 * u), 125, 290)
        p.lineTo(37 * u, 22 * u)
    else:
        p.lineTo(8.5 * u, 50 * u)
        p.quadTo(6 * u, 56 * u, 12 * u, 56 * u)
        p.lineTo(52 * u, 56 * u)
        p.quadTo(58 * u, 56 * u, 55.5 * u, 50 * u)
        p.lineTo(37 * u, 22 * u)
    p.closeSubpath()
    return p


def _flame_color(t: float) -> QColor:
    """The flame gradient at `t` in 0..1."""
    for (t0, c0), (t1, c1) in zip(FLAME, FLAME[1:]):
        if t <= t1:
            f = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            a, b = QColor(c0), QColor(c1)
            return QColor(int(a.red() + (b.red() - a.red()) * f), int(a.green() + (b.green() - a.green()) * f),
                          int(a.blue() + (b.blue() - a.blue()) * f))
    return QColor(FLAME[-1][1])


def paint_logo(painter: QPainter, size: float, x: float = 0.0, y: float = 0.0, variant: str = MAIN, ink: QColor | None = None) -> None:
    """Paint the mark into a `size` × `size` square at (x, y); `variant` is a key of `VARIANTS`, `ink` overrides the stroke colour."""
    u = size / 64.0
    ink = ink or INK
    round_bottom = variant == ROUND
    painter.save()
    painter.translate(x, y)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    small = size < 40
    # the glass
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(30, 136, 229, 22) if size >= 32 and variant != MONO else Qt.BrushStyle.NoBrush)
    painter.drawPath(_body_path(u, round_bottom))
    # the spiral: circles (or squares) shrinking by the golden ratio along a logarithmic spiral, clipped to the body
    painter.save()
    painter.setClipPath(_body_path(u, round_bottom))
    cx, cy = (32.5 * u, 41 * u) if not round_bottom else (32 * u, 40 * u)
    count = 6 if small else 12
    for i in range(count):
        k = i / max(1, count - 1)
        angle = 2.4 + i * 0.82                       # clockwise, from the bottom-left of the body inwards
        radius = 14.5 * u * GOLDEN ** (-i * 0.36)
        dist = 18.0 * u * GOLDEN ** (-i * 0.36)
        dot = QPointF(cx + dist * math.cos(angle), cy + dist * math.sin(angle) * 0.8)
        if variant == MONO:
            painter.setBrush(QBrush(ink))
            painter.setPen(QPen(QColor(255, 255, 255), max(0.8, 1.3 * u)) if not small else Qt.PenStyle.NoPen)
        else:
            painter.setBrush(QBrush(_flame_color(k)))
            painter.setPen(QPen(QColor(255, 255, 255, 110), max(0.6, 0.9 * u)) if not small else Qt.PenStyle.NoPen)
        if variant == SQUARES:
            painter.save()
            painter.translate(dot)
            painter.rotate(math.degrees(angle) * 0.5)
            painter.drawRect(QRectF(-radius * 0.9, -radius * 0.9, radius * 1.8, radius * 1.8))
            painter.restore()
        else:
            painter.drawEllipse(dot, radius, radius)
    painter.restore()
    # the flask outline
    pen = QPen(ink, max(1.5, (5.2 if small else 4.4) * u), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(_flask_path(u, round_bottom))
    # the bubbles in the neck
    if not small:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(ink if variant == MONO else BUBBLE)
        if variant == TRIANGLES:
            for (bx, by, r) in ((32, 16.5, 2.4), (30.5, 11, 1.5)):
                painter.drawPolygon(QPolygonF([QPointF(bx * u, (by - r) * u), QPointF((bx - r) * u, (by + r * 0.7) * u),
                                               QPointF((bx + r) * u, (by + r * 0.7) * u)]))
        else:
            painter.drawEllipse(QPointF(32 * u, 16.5 * u), 2.0 * u, 2.0 * u)
            painter.drawEllipse(QPointF(30.5 * u, 11 * u), 1.2 * u, 1.2 * u)
    painter.restore()


def logo_pixmap(size: int, background: QColor | None = None, variant: str = MAIN, ink: QColor | None = None) -> QPixmap:
    """The mark at `size` pixels (transparent, or on `background`)."""
    pixmap = QPixmap(size, size)
    pixmap.fill(background if background is not None else Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    paint_logo(painter, size, variant=variant, ink=ink)
    painter.end()
    return pixmap


def logo_icon() -> QIcon:
    """The mark at every size a window icon or task bar may ask for."""
    icon = QIcon()
    for size in SIZES:
        icon.addPixmap(logo_pixmap(size))
    return icon


def wordmark_pixmap(height: int = 96, background: QColor | None = None, dark: bool = False, variant: str = MAIN) -> QPixmap:
    """The mark beside the name: `Fractal` in ink, `chemy` in the accent blue, for headers and the About box."""
    mark = height
    font = QFont("Sans Serif")
    font.setPixelSize(int(height * 0.42))
    font.setWeight(QFont.Weight.DemiBold)
    font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 101)
    probe = QPixmap(1, 1)
    painter = QPainter(probe)
    painter.setFont(font)
    width_a = painter.fontMetrics().horizontalAdvance("Fractal")
    width_b = painter.fontMetrics().horizontalAdvance("chemy")
    painter.end()
    pixmap = QPixmap(mark + int(height * 0.18) + width_a + width_b + int(height * 0.2), height)
    pixmap.fill(background if background is not None else Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    paint_logo(painter, mark, variant=variant, ink=QColor("#e8ecf5") if dark and variant == MONO else None)
    painter.setFont(font)
    x = mark + int(height * 0.18)
    baseline = int(height * 0.63)
    painter.setPen(QColor("#e8ecf5") if dark else INK)
    painter.drawText(x, baseline, "Fractal")
    painter.setPen(QColor("#42a5f5") if dark else BUBBLE)
    painter.drawText(x + width_a, baseline, "chemy")
    painter.end()
    return pixmap


__all__ = ["paint_logo", "logo_pixmap", "logo_icon", "wordmark_pixmap", "SIZES", "FLAME", "INK", "VARIANTS", "MAIN", "MONO", "SQUARES",
           "ROUND", "TRIANGLES"]
