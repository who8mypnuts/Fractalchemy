"""The shared fractal scene: what a flame *means*, independent of how it is rendered.

Both engines (the interactive GPU preview and the precision final renderer) consume
these definitions, so the camera, formulas, colouring and palette agree everywhere.
"""

from .scene import Camera, Coloring, Flame, XForm, identity_affine

__all__ = ["Camera", "Coloring", "Flame", "XForm", "identity_affine"]
