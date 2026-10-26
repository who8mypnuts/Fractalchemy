"""Convert between gradient positions (0..1) and widget x pixels.

Both the colour strip and the node bar use this so nodes stay aligned with
the colours they control, regardless of widget size.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..model.color import clamp_unit


@dataclass(frozen=True)
class PositionMapper:
    width: int
    margin: int

    @property
    def usable_width(self) -> int:
        return max(1, self.width - 2 * self.margin)

    def to_x(self, position: float) -> float:
        return self.margin + clamp_unit(position) * self.usable_width

    def to_position(self, x: float) -> float:
        return clamp_unit((x - self.margin) / self.usable_width)
