"""Whole-gradient adjustments: rotation and hue / saturation / luminance shifts.

These are applied to a *base* gradient every time a parameter changes, so
dragging a slider back and forth is lossless and never accumulates clipping.
"""

from __future__ import annotations

import colorsys
from dataclasses import dataclass

from .color import RGB, clamp_channel
from .gradient import Gradient
from .stop import ColorStop

ROTATION_STEPS = 400   # one full turn; matches Ultra Fractal's 0..399 index resolution
ROTATION_RANGE = ROTATION_STEPS // 2   # slider runs -200 .. +200


@dataclass(frozen=True)
class Adjustments:
    rotation: int = 0      # -ROTATION_RANGE .. +ROTATION_RANGE, in 1/400ths of the gradient
    hue: int = 0           # degrees, -180 .. 180
    saturation: int = 0    # percent, -100 .. 100
    luminance: int = 0     # percent, -100 .. 100

    @property
    def is_identity(self) -> bool:
        return self == Adjustments()


def apply_adjustments(base: Gradient, adj: Adjustments) -> Gradient:
    stops = [ColorStop(s.position, shift_hsl(s.color, adj.hue, adj.saturation, adj.luminance)) for s in base.stops]
    return Gradient(base.name, rotate_stops(stops, adj.rotation / ROTATION_STEPS))


def rotate_stops(stops: list[ColorStop], amount: float) -> list[ColorStop]:
    """Shift every stop by `amount` of the gradient length, wrapping around the ends.

    Two stops can only coincide after rotating if they were a full length apart
    (the old start and end meeting at the seam); the old *end* is placed first
    so the seam reads end → start, exactly as the original did across 1.0 → 0.0.
    """
    if amount == 0:
        return [s.copy() for s in stops]
    moved = [((s.position + amount) % 1.0, -s.position, ColorStop((s.position + amount) % 1.0, s.color)) for s in stops]
    return [stop for _, _, stop in sorted(moved, key=lambda m: (m[0], m[1]))]


def shift_hsl(color: RGB, hue_degrees: float, saturation_pct: float, luminance_pct: float) -> RGB:
    r, g, b = (c / 255.0 for c in color)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    h = (h + hue_degrees / 360.0) % 1.0
    s = _push(s, saturation_pct / 100.0)
    l = _push(l, luminance_pct / 100.0)
    return tuple(clamp_channel(c * 255) for c in colorsys.hls_to_rgb(h, l, s))  # type: ignore[return-value]


def _push(value: float, amount: float) -> float:
    """Move `value` (0..1) toward 1 for positive amounts, toward 0 for negative; ±1 reaches the end."""
    if amount >= 0:
        return value + (1.0 - value) * amount
    return value * (1.0 + amount)
