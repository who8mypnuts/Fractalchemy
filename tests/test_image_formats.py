"""Decoding of the modern image types. Fixtures are generated, not committed."""

import pytest
from PIL import Image

from fractalchemy.formats import load_gradient
from fractalchemy.imaging import supported_image_extensions

SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">'
    '<rect width="100" height="100" fill="#ff0000"/><circle cx="150" cy="50" r="40" fill="#0000ff"/></svg>'
)


@pytest.fixture(scope="module")
def photo(samples) -> Image.Image:
    image = Image.open(samples / "sample images" / "idaho-002.jpeg").convert("RGB")
    image.thumbnail((160, 160))
    return image


def _dominant(gradient):
    return {s.color for s in gradient.stops}


def _close(colors, target, tol=12):
    return any(max(abs(a - b) for a, b in zip(c, target)) <= tol for c in colors)


@pytest.mark.parametrize("ext", [".avif", ".heic", ".jxl"])
def test_modern_raster_formats_decode(tmp_path, photo, ext):
    assert ext in supported_image_extensions()
    path = tmp_path / f"photo{ext}"
    photo.save(path)
    gradient = load_gradient(path)
    assert 8 <= len(gradient) <= 16
    assert _close(_dominant(gradient), (40, 83, 137))  # the lake blue present in every encode


def test_apng_uses_first_frame_only(tmp_path, photo):
    red, green = Image.new("RGB", photo.size, (255, 0, 0)), Image.new("RGB", photo.size, (0, 255, 0))
    path = tmp_path / "anim.apng"
    photo.save(path, save_all=True, append_images=[red, green], duration=50, loop=0)
    colors = _dominant(load_gradient(path))
    assert not _close(colors, (255, 0, 0)) and not _close(colors, (0, 255, 0))


def test_svg_is_rasterised_and_transparency_ignored(tmp_path, qapp):
    path = tmp_path / "shapes.svg"
    path.write_text(SVG)
    colors = _dominant(load_gradient(path))
    assert _close(colors, (255, 0, 0)) and _close(colors, (0, 0, 255))
    assert not _close(colors, (0, 0, 0), tol=40)  # transparent background never becomes black


def test_transparent_png_ignores_alpha_zero_pixels(tmp_path):
    image = Image.new("RGBA", (50, 50), (0, 0, 0, 0))
    for x in range(25):
        for y in range(50):
            image.putpixel((x, y), (200, 30, 30, 255))
    path = tmp_path / "half.png"
    image.save(path)
    assert _dominant(load_gradient(path)) == {(200, 30, 30)}
