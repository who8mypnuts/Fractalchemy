"""Qt-free gradient model: an ordered list of colour stops."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

from .color import RGB, clamp_unit, lerp_rgb
from .stop import ColorStop


@dataclass
class Gradient:
    name: str = "untitled"
    stops: list[ColorStop] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._sort()

    # --- construction -------------------------------------------------------
    @classmethod
    def from_colors(cls, name: str, colors: Sequence[RGB]) -> "Gradient":
        """Evenly space the given colours across 0..1."""
        if not colors:
            return cls(name)
        step = 1.0 / max(1, len(colors) - 1)
        return cls(name, [ColorStop(i * step, c) for i, c in enumerate(colors)])

    # --- queries ------------------------------------------------------------
    def __len__(self) -> int:
        return len(self.stops)

    def color_at(self, t: float) -> RGB:
        """Linear interpolation between neighbouring stops; clamped at the ends."""
        if not self.stops:
            return (0, 0, 0)
        t = clamp_unit(t)
        if t <= self.stops[0].position:
            return self.stops[0].color
        if t >= self.stops[-1].position:
            return self.stops[-1].color
        left, right = self._neighbours(t)
        span = right.position - left.position
        if span <= 0:
            return right.color
        return lerp_rgb(left.color, right.color, (t - left.position) / span)

    def sample(self, count: int) -> list[RGB]:
        """Evaluate the gradient at `count` evenly spaced points."""
        if count <= 1:
            return [self.color_at(0.0)] * max(count, 0)
        return [self.color_at(i / (count - 1)) for i in range(count)]

    def index_of(self, stop: ColorStop) -> int:
        """Current index of this exact stop object (stops may be reordered by moves)."""
        for i, candidate in enumerate(self.stops):
            if candidate is stop:
                return i
        raise ValueError("stop does not belong to this gradient")

    # --- mutation -----------------------------------------------------------
    def move_stop(self, index: int, position: float) -> int:
        """Move a stop anywhere in 0..1, passing over neighbours if needed.

        Other stops keep their positions; the list is re-sorted so the
        invariant holds. Returns the stop's new index.
        """
        stop = self.stops[index]
        stop.position = clamp_unit(position)
        self._sort()
        return self.index_of(stop)

    def set_color(self, index: int, color: RGB) -> None:
        self.stops[index].color = color

    def copy(self) -> "Gradient":
        return Gradient(self.name, [s.copy() for s in self.stops])

    # --- internals ----------------------------------------------------------
    def _sort(self) -> None:
        self.stops.sort(key=lambda s: s.position)  # stable: equal positions keep order

    def _neighbours(self, t: float) -> tuple[ColorStop, ColorStop]:
        for left, right in zip(self.stops, self.stops[1:]):
            if left.position <= t <= right.position:
                return left, right
        return self.stops[-1], self.stops[-1]


def evenly_spaced(colors: Iterable[RGB], name: str = "untitled") -> Gradient:
    return Gradient.from_colors(name, list(colors))
