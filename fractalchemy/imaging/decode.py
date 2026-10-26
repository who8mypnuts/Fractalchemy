"""Turn any supported image file into a small RGB Pillow image ready for analysis."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from .plugins import is_svg, supported_image_extensions


def load_for_analysis(path: Path, max_edge: int) -> Image.Image:
    """First frame, downscaled, transparent pixels removed, as an RGB image."""
    supported_image_extensions()  # ensures optional decoders are registered
    if is_svg(path.suffix):
        from .svg import rasterize_svg  # Qt import kept lazy

        image = rasterize_svg(path, max_edge)
    else:
        with Image.open(path) as source:
            source.seek(0)  # animated formats (APNG, GIF, AVIF sequences): first frame
            image = source.convert("RGBA")
    image.thumbnail((max_edge, max_edge))
    return _opaque_pixels(image)


def _opaque_pixels(image: Image.Image) -> Image.Image:
    """Flatten to a 1-row RGB image of only visible pixels, so transparency
    (common in SVG/PNG/AVIF) never pollutes the palette with black."""
    pixels = [(r, g, b) for r, g, b, a in image.getdata() if a > 0]
    if not pixels:
        raise ValueError("Image has no visible pixels")
    flat = Image.new("RGB", (len(pixels), 1))
    flat.putdata(pixels)
    return flat
