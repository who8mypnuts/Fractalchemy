"""Whole-gradient adjustments: rotation and hue / saturation / luminance shifts.

These are applied to a *base* gradient every time a parameter changes, so
dragging a slider back and forth is lossless and never accumulates clipping.
"""

from __future__ import annotations

from dataclasses import dataclass

from .color import RGB, hsl_to_rgb, rgb_to_hsl
from .gradient import Gradient
from .stop import ColorStop

ROTATION_STEPS = 400   # one full turn; matches Ultra Fractal's 0..399 index resolution
ROTATION_RANGE = ROTATION_STEPS // 2   # slider runs -200 .. +200


@dataclass(frozen=True)
class Adjustments:
    """The four whole-gradient slider values.

    Attributes:
        rotation: Shift in 1/400ths of the gradient, -200..200 (one full turn).
        hue: Hue shift in degrees, -180..180.
        saturation: Saturation push in percent, -100 (grey) .. 100 (vivid).
        luminance: Lightness push in percent, -100 (black) .. 100 (white).
    """
    rotation: int = 0
    hue: int = 0
    saturation: int = 0
    luminance: int = 0

    @property
    def is_identity(self) -> bool:
        """True when every value is zero, i.e. applying them changes nothing."""
        return self == Adjustments()


def apply_adjustments(base: Gradient, adj: Adjustments) -> Gradient:
    """Derive a new gradient from `base` with the adjustments applied.

    The base is never mutated, so repeated calls with different values are
    lossless.
    """
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
    """Shift one colour's hue and push its saturation and lightness.

    Args:
        color: Source RGB colour.
        hue_degrees: Added to the hue (wraps around the colour wheel).
        saturation_pct: -100..100; negative moves toward grey, positive toward vivid.
        luminance_pct: -100..100; negative moves toward black, positive toward white.

    Returns:
        The adjusted 8-bit RGB colour.
    """
    h, s, l = rgb_to_hsl(color)
    return hsl_to_rgb(h + hue_degrees / 360.0, _push(s, saturation_pct / 100.0), _push(l, luminance_pct / 100.0))


def _push(value: float, amount: float) -> float:
    """Move `value` (0..1) toward 1 for positive amounts, toward 0 for negative; ±1 reaches the end."""
    if amount >= 0:
        return value + (1.0 - value) * amount
    return value * (1.0 + amount)
