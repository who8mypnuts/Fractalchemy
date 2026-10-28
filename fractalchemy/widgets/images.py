"""numpy ↔ QImage conversions shared by the viewport, thumbnails and previews."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPixmap


def rgba_to_qimage(rgba: np.ndarray) -> QImage:
    """An independent QImage from an (H, W, 4) uint8 RGBA array (the array may be released afterwards)."""
    if rgba.ndim != 3 or rgba.shape[2] != 4 or rgba.dtype != np.uint8:
        raise ValueError(f"expected an (H, W, 4) uint8 array, got {rgba.shape} {rgba.dtype}")
    height, width = rgba.shape[:2]
    data = np.ascontiguousarray(rgba)
    return QImage(data.data, width, height, width * 4, QImage.Format.Format_RGBA8888).copy()


def palette_pixmap(palette, width: int, height: int = 14) -> QPixmap:
    """A palette (RGB triples, 0..255) as a horizontal strip of `width` × `height` pixels."""
    image = QImage(max(1, len(palette)), 1, QImage.Format.Format_RGB32)
    for i, (r, g, b) in enumerate(palette):
        image.setPixelColor(i, 0, QColor(int(r), int(g), int(b)))
    return QPixmap.fromImage(image.scaled(max(1, width), height, Qt.AspectRatioMode.IgnoreAspectRatio,
                                          Qt.TransformationMode.FastTransformation))
