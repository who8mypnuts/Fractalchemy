"""Solid rendering (the 3D Editor): the point cloud as a lit surface — numpy reference, G-buffer, shading."""

from .gbuffer import GBuffer, ShadowMap, downsample
from .shading import shade
from .view import View, light_direction

__all__ = ["GBuffer", "ShadowMap", "downsample", "shade", "View", "light_direction"]
