"""Pull a compact, weighted palette out of a raster image using Pillow."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from ..model import RGB

WeightedColor = tuple[RGB, int]  # (rgb, pixel count)


def extract_palette(path: Path, color_count: int, analysis_size: int) -> list[WeightedColor]:
    with Image.open(path) as source:
        image = _prepare(source, analysis_size)
    quantized = image.quantize(colors=color_count, method=Image.Quantize.MEDIANCUT)
    return _weighted_palette(quantized)


def _prepare(image: Image.Image, max_edge: int) -> Image.Image:
    rgb = image.convert("RGB")
    rgb.thumbnail((max_edge, max_edge))
    return rgb


def _weighted_palette(quantized: Image.Image) -> list[WeightedColor]:
    palette = quantized.getpalette()
    counts = quantized.getcolors() or []
    result: list[WeightedColor] = []
    for count, index in counts:
        rgb = tuple(palette[index * 3:index * 3 + 3])
        result.append((rgb, count))  # type: ignore[arg-type]
    result.sort(key=lambda item: item[1], reverse=True)
    return result
