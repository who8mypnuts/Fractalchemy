"""A single colour node on a gradient."""

from __future__ import annotations

from dataclasses import dataclass

from .color import RGB


@dataclass
class ColorStop:
    position: float  # 0.0 .. 1.0
    color: RGB

    def copy(self) -> "ColorStop":
        return ColorStop(self.position, self.color)
