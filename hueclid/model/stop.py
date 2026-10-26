"""A single colour node on a gradient."""

from __future__ import annotations

from dataclasses import dataclass

from .color import RGB


@dataclass
class ColorStop:
    """A colour node on a gradient.

    Attributes:
        position: Where the node sits along the gradient, 0.0 (start) to 1.0 (end).
        color: The node's 8-bit RGB colour.
    """
    position: float
    color: RGB

    def copy(self) -> "ColorStop":
        """Return an independent copy of this stop."""
        return ColorStop(self.position, self.color)
