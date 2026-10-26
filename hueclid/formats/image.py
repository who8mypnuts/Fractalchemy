"""Treat any raster image as a gradient source by extracting its palette."""

from __future__ import annotations

from pathlib import Path

from .. import config
from ..imaging import extract_palette, order_colors
from ..model import Gradient
from .base import GradientFormat


class ImageFormat(GradientFormat):
    name = "Image"
    extensions = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp")
    can_save = False  # image-derived gradients are written out as .ugr

    def load(self, path: Path) -> list[Gradient]:
        weighted = extract_palette(path, config.IMAGE_COLOR_COUNT, config.IMAGE_ANALYSIS_SIZE)
        ordered = order_colors(weighted, config.IMAGE_ORDERING)
        return [Gradient.from_colors(path.stem, ordered)]
