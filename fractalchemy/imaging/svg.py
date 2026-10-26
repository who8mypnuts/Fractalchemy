"""Rasterise an SVG to a Pillow image using Qt's SVG renderer (needs a QGuiApplication)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


def rasterize_svg(path: Path, max_edge: int) -> Image.Image:
    """Render an SVG file to an RGBA Pillow image no larger than `max_edge` on either side.

    Raises:
        ValueError: If Qt cannot parse the file as SVG.
    """
    renderer = QSvgRenderer(str(path))
    if not renderer.isValid():
        raise ValueError(f"{path.name} is not a valid SVG")
    size = _target_size(renderer.defaultSize(), max_edge)
    return _to_pillow(_render(renderer, size))


def _target_size(default: QSize, max_edge: int) -> QSize:
    if default.isEmpty():
        default = QSize(max_edge, max_edge)
    return default.scaled(max_edge, max_edge, Qt.AspectRatioMode.KeepAspectRatio)


def _render(renderer: QSvgRenderer, size: QSize) -> QImage:
    image = QImage(size, QImage.Format.Format_RGBA8888)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    return image


def _to_pillow(image: QImage) -> Image.Image:
    raw = bytes(image.constBits())
    size = (image.width(), image.height())
    return Image.frombuffer("RGBA", size, raw, "raw", "RGBA", image.bytesPerLine(), 1).copy()
