"""Bridges between the Qt-free model colours and QColor / QLinearGradient."""

from __future__ import annotations

from PySide6.QtGui import QColor, QLinearGradient

from ..model import RGB, Gradient
from ..model.color import luminance

LIGHT_THRESHOLD = 140  # luminance above which black text / outlines read better than white


def to_qcolor(rgb: RGB) -> QColor:
    """QColor for an RGB triple."""
    return QColor(*rgb)


def to_qgradient(gradient: Gradient, x0: float, x1: float) -> QLinearGradient:
    """A horizontal QLinearGradient matching Gradient.color_at semantics (cyclic ends)."""
    qgrad = QLinearGradient(x0, 0, x1, 0)
    if gradient.stops and gradient.stops[0].position > 0.0:
        qgrad.setColorAt(0.0, to_qcolor(gradient.color_at(0.0)))
    for stop in gradient.stops:
        qgrad.setColorAt(stop.position, to_qcolor(stop.color))
    if gradient.stops and gradient.stops[-1].position < 1.0:
        qgrad.setColorAt(1.0, to_qcolor(gradient.color_at(1.0)))
    return qgrad


def contrasting_pen_color(rgb: RGB) -> QColor:
    """Black for light colours, white for dark ones, so outlines and text stay legible."""
    return QColor(0, 0, 0) if luminance(rgb) > LIGHT_THRESHOLD else QColor(255, 255, 255)
