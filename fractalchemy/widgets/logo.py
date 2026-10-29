"""The proposed Fractalchemy mark: an alchemist's flask whose contents are a fractal spiral.

The flask is the alchemical sign for fire (a triangle) with a neck — one bold, rounded stroke that stays
crisp at 16 px — and inside it a logarithmic spiral of circles that shrink by the golden ratio (the
self-similarity of a fractal) coloured by the app's flame gradient, ember orange through magenta to the
accent blue. Two bubbles rise in the neck. `logo_pixmap(size)` paints it at any size; `logo_icon()` is the
multi-size QIcon for windows and the task bar; `wordmark_pixmap()` sets the mark beside the name.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap

INK = QColor("#1f2a44")                 # the flask: deep indigo
INK_LIGHT = QColor("#33405f")
FLAME = ((0.0, "#ffb347"), (0.35, "#ff6a00"), (0.7, "#e6007e"), (1.0, "#1e88e5"))
BUBBLE = QColor("#1e88e5")
GOLDEN = (1 + 5 ** 0.5) / 2
SIZES = (16, 24, 32, 48, 64, 128, 256)


def _flask_path(u: float) -> QPainterPath:
    """The flask outline on a 64-unit grid, scaled by `u`: lip, neck, flaring body, rounded bottom."""
    p = QPainterPath()
    p.moveTo(24 * u, 7 * u)
    p.lineTo(40 * u, 7 * u)                    # the lip
    p.moveTo(27 * u, 7 * u)
    p.lineTo(27 * u, 22 * u)                   # the neck
    p.lineTo(8.5 * u, 50 * u)                  # the body flares out
    p.quadTo(6 * u, 56 * u, 12 * u, 56 * u)    # rounded bottom-left
    p.lineTo(52 * u, 56 * u)
    p.quadTo(58 * u, 56 * u, 55.5 * u, 50 * u)  # rounded bottom-right
    p.lineTo(37 * u, 22 * u)
    p.lineTo(37 * u, 7 * u)
    return p


def _body_path(u: float) -> QPainterPath:
    """The closed body, for the glass tint and for clipping the spiral."""
    p = QPainterPath()
    p.moveTo(27 * u, 22 * u)
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


def paint_logo(painter: QPainter, size: float, x: float = 0.0, y: float = 0.0) -> None:
    """Paint the mark into a `size` × `size` square at (x, y)."""
    u = size / 64.0
    painter.save()
    painter.translate(x, y)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    small = size < 40
    # the glass
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(30, 136, 229, 22) if size >= 32 else Qt.BrushStyle.NoBrush)
    painter.drawPath(_body_path(u))
    # the spiral: circles shrinking by the golden ratio along a logarithmic spiral, clipped to the body
    painter.save()
    painter.setClipPath(_body_path(u))
    cx, cy = 32.5 * u, 41 * u
    count = 6 if small else 12
    for i in range(count):
        k = i / max(1, count - 1)
        angle = 2.4 + i * 0.82                       # clockwise, from the bottom-left of the body inwards
        radius = 14.5 * u * GOLDEN ** (-i * 0.36)
        dist = 18.0 * u * GOLDEN ** (-i * 0.36)
        dot = QPointF(cx + dist * math.cos(angle), cy + dist * math.sin(angle) * 0.8)
        color = _flame_color(k)
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(QColor(255, 255, 255, 110), max(0.6, 0.9 * u)) if not small else Qt.PenStyle.NoPen)
        painter.drawEllipse(dot, radius, radius)
    painter.restore()
    # the flask outline
    pen = QPen(INK, max(1.5, (5.2 if small else 4.4) * u), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(_flask_path(u))
    # the bubbles in the neck
    if not small:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(BUBBLE)
        painter.drawEllipse(QPointF(32 * u, 16.5 * u), 2.0 * u, 2.0 * u)
        painter.drawEllipse(QPointF(30.5 * u, 11 * u), 1.2 * u, 1.2 * u)
    painter.restore()


def logo_pixmap(size: int, background: QColor | None = None) -> QPixmap:
    """The mark at `size` pixels (transparent, or on `background`)."""
    pixmap = QPixmap(size, size)
    pixmap.fill(background if background is not None else Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    paint_logo(painter, size)
    painter.end()
    return pixmap


def logo_icon() -> QIcon:
    """The mark at every size a window icon or task bar may ask for."""
    icon = QIcon()
    for size in SIZES:
        icon.addPixmap(logo_pixmap(size))
    return icon


def wordmark_pixmap(height: int = 96, background: QColor | None = None, dark: bool = False) -> QPixmap:
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
    paint_logo(painter, mark)
    painter.setFont(font)
    x = mark + int(height * 0.18)
    baseline = int(height * 0.63)
    painter.setPen(QColor("#e8ecf5") if dark else INK)
    painter.drawText(x, baseline, "Fractal")
    painter.setPen(QColor("#42a5f5") if dark else BUBBLE)
    painter.drawText(x + width_a, baseline, "chemy")
    painter.end()
    return pixmap


__all__ = ["paint_logo", "logo_pixmap", "logo_icon", "wordmark_pixmap", "SIZES", "FLAME", "INK"]
