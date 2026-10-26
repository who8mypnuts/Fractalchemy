"""Strategies for arranging an unordered palette into a left-to-right gradient."""

from __future__ import annotations

from typing import Callable

from ..model import RGB
from ..model.color import distance, hue, luminance
from .extract import WeightedColor

Strategy = Callable[[list[RGB]], list[RGB]]


def by_luminance(colors: list[RGB]) -> list[RGB]:
    """Darkest to brightest."""
    return sorted(colors, key=luminance)


def by_hue(colors: list[RGB]) -> list[RGB]:
    """Around the colour wheel starting at red."""
    return sorted(colors, key=hue)


def by_path(colors: list[RGB]) -> list[RGB]:
    """Greedy nearest-neighbour walk from the darkest colour: smooth transitions."""
    if not colors:
        return []
    remaining = list(colors)
    current = min(remaining, key=luminance)
    remaining.remove(current)
    ordered = [current]
    while remaining:
        current = min(remaining, key=lambda c: distance(c, ordered[-1]))
        remaining.remove(current)
        ordered.append(current)
    return ordered


STRATEGIES: dict[str, Strategy] = {
    "luminance": by_luminance,
    "hue": by_hue,
    "path": by_path,
}


def order_colors(weighted: list[WeightedColor], strategy: str = "path") -> list[RGB]:
    """Arrange extracted colours using the named strategy from STRATEGIES.

    Raises:
        ValueError: If `strategy` is not a known name.
    """
    try:
        order = STRATEGIES[strategy]
    except KeyError:
        raise ValueError(f"Unknown ordering '{strategy}'; choose from {sorted(STRATEGIES)}")
    return order([rgb for rgb, _ in weighted])
