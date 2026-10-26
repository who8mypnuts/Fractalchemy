"""Edits that touch a single node: insert after, recolour, delete."""

from __future__ import annotations

import random

from .adjust import shift_hsl
from .color import RGB
from .gradient import Gradient
from .operations import MIN_NODES, _pick, _random_palette
from .stop import ColorStop


def position_after(gradient: Gradient, index: int) -> float:
    """Midway between node `index` and the next one (or the end of the gradient)."""
    stops = gradient.stops
    here = stops[index].position
    if index + 1 < len(stops):
        return (here + stops[index + 1].position) / 2
    if here < 1.0:
        return (here + 1.0) / 2
    previous = stops[index - 1].position if index > 0 else 0.0
    return (here + previous) / 2  # already at the very end: slot it just before


def inserted_after(gradient: Gradient, index: int, color: RGB) -> tuple[list[ColorStop], int]:
    """New stop list with `color` added after node `index`, and the new node's index."""
    stop = ColorStop(position_after(gradient, index), color)
    stops = [s.copy() for s in gradient.stops]
    stops.append(stop)
    stops.sort(key=lambda s: s.position)
    return stops, next(i for i, s in enumerate(stops) if s is stop)


def without(gradient: Gradient, index: int) -> list[ColorStop]:
    """Copy of the stops with node `index` removed.

    Raises:
        ValueError: If removing it would leave fewer than MIN_NODES stops.
    """
    if len(gradient.stops) <= MIN_NODES:
        raise ValueError(f"A gradient needs at least {MIN_NODES} nodes")
    return [s.copy() for i, s in enumerate(gradient.stops) if i != index]


def random_color(rng: random.Random | None = None) -> RGB:
    """An entirely new colour (from a random harmony so it is still pleasant)."""
    rng = rng or random.Random()
    return _pick(_random_palette(rng), rng)


def perturbed_color(color: RGB, rng: random.Random | None = None) -> RGB:
    """The same colour nudged a noticeable but not wild amount in hue / saturation / lightness."""
    rng = rng or random.Random()
    hue = rng.choice((-1, 1)) * rng.uniform(20, 90)
    return shift_hsl(color, hue, rng.uniform(-35, 35), rng.uniform(-25, 25))
