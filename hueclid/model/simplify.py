"""Reduce a dense list of stops to the few that actually shape the gradient.

Uses Ramer-Douglas-Peucker over (position, colour): a stop is dropped when the
straight-line blend between its surviving neighbours reproduces it within
`tolerance` on every channel.
"""

from __future__ import annotations

from .color import lerp_rgb, max_channel_delta
from .stop import ColorStop


def simplify(stops: list[ColorStop], tolerance: int) -> list[ColorStop]:
    """Drop stops that a straight blend between their neighbours reproduces.

    Args:
        stops: Stops sorted by position.
        tolerance: Maximum per-channel error (0..255) allowed when dropping a stop;
            0 keeps everything.

    Returns:
        A new list of copied stops, always including the first and last.
    """
    if tolerance <= 0 or len(stops) <= 2:
        return [s.copy() for s in stops]
    keep = [False] * len(stops)
    keep[0] = keep[-1] = True
    _mark_required(stops, 0, len(stops) - 1, tolerance, keep)
    return [s.copy() for s, k in zip(stops, keep) if k]


def _mark_required(stops, first: int, last: int, tolerance: int, keep: list[bool]) -> None:
    worst_index, worst_delta = _furthest_from_chord(stops, first, last)
    if worst_index is None or worst_delta <= tolerance:
        return
    keep[worst_index] = True
    _mark_required(stops, first, worst_index, tolerance, keep)
    _mark_required(stops, worst_index, last, tolerance, keep)


def _furthest_from_chord(stops, first: int, last: int) -> tuple[int | None, int]:
    a, b = stops[first], stops[last]
    span = b.position - a.position
    worst_index, worst_delta = None, -1
    for i in range(first + 1, last):
        s = stops[i]
        t = (s.position - a.position) / span if span > 0 else 0.0
        delta = max_channel_delta(s.color, lerp_rgb(a.color, b.color, t))
        if delta > worst_delta:
            worst_index, worst_delta = i, delta
    return worst_index, worst_delta
