"""Qt-free gradient model: an ordered list of colour stops."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

from .color import RGB, clamp_unit, lerp_rgb
from .stop import ColorStop


@dataclass
class Gradient:
    """An ordered, cyclic list of colour stops.

    The stop list is kept sorted by position at all times. Colours between
    stops are linearly interpolated; beyond the first or last stop the colour
    wraps around (last stop back to first), matching Ultra Fractal / Apophysis.

    Attributes:
        name: The gradient's title as shown in the UI and written to files.
        stops: The colour nodes, sorted by position.
    """
    name: str = "untitled"
    stops: list[ColorStop] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Enforce the sorted-stops invariant for stops passed to the constructor."""
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
        """Number of colour stops."""
        return len(self.stops)

    def color_at(self, t: float) -> RGB:
        """Linear interpolation between neighbouring stops.

        The gradient is cyclic (as in Ultra Fractal / Apophysis): outside the
        first..last span the colour blends from the last stop back to the first.
        """
        if not self.stops:
            return (0, 0, 0)
        t = clamp_unit(t)
        first, last = self.stops[0], self.stops[-1]
        if t < first.position or t > last.position:
            return self._wrap_color(t)
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
        """Recolour the stop at `index`."""
        self.stops[index].color = color

    def copy(self) -> "Gradient":
        """Return a deep copy (stops are new objects)."""
        return Gradient(self.name, [s.copy() for s in self.stops])

    # --- internals ----------------------------------------------------------
    def _sort(self) -> None:
        self.stops.sort(key=lambda s: s.position)  # stable: equal positions keep order

    def _wrap_color(self, t: float) -> RGB:
        first, last = self.stops[0], self.stops[-1]
        span = first.position + (1.0 - last.position)
        if span <= 0:
            return first.color
        return lerp_rgb(last.color, first.color, ((t - last.position) % 1.0) / span)

    def _neighbours(self, t: float) -> tuple[ColorStop, ColorStop]:
        for left, right in zip(self.stops, self.stops[1:]):
            if left.position <= t <= right.position:
                return left, right
        return self.stops[-1], self.stops[-1]


def evenly_spaced(colors: Iterable[RGB], name: str = "untitled") -> Gradient:
    """Build a gradient whose colours are spread evenly across 0..1."""
    return Gradient.from_colors(name, list(colors))
