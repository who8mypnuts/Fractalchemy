"""Treat any raster (or SVG) image as a gradient source by extracting its palette."""

from __future__ import annotations

from pathlib import Path

from .. import config
from ..imaging import extract_palette, order_colors, supported_image_extensions
from ..model import Gradient
from .base import GradientFormat


class ImageFormat(GradientFormat):
    name = "Image"
    can_save = False  # image-derived gradients are written out as .ugr

    def __init__(self) -> None:
        self.extensions = supported_image_extensions()  # depends on installed decoders

    def load(self, path: Path) -> list[Gradient]:
        weighted = extract_palette(path, config.IMAGE_COLOR_COUNT, config.IMAGE_ANALYSIS_SIZE)
        ordered = order_colors(weighted, config.IMAGE_ORDERING)
        return [Gradient.from_colors(path.stem, ordered)]
