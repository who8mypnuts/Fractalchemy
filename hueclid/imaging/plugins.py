"""Register optional Pillow decoders and report which image types are usable.

Pillow handles PNG/APNG/JPEG/AVIF/WebP/... natively. HEIC and JPEG XL need
plugins; SVG is rasterised through Qt (see svg.py). Anything whose decoder is
missing is simply left out of the supported extension list.
"""

from __future__ import annotations

import importlib
from functools import cache

from PIL import Image, features

NATIVE_EXTENSIONS = (".png", ".apng", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp")
SVG_EXTENSIONS = (".svg", ".svgz")

# (extensions, module that provides them, registration hook or None)
_OPTIONAL = (
    ((".avif",), None, lambda: features.check("avif")),
    ((".heic", ".heif"), "pillow_heif", lambda mod: mod.register_heif_opener()),
    ((".jxl",), "pillow_jxl", lambda mod: True),  # importing registers the codec
)


@cache
def supported_image_extensions() -> tuple[str, ...]:
    """Every extension we can decode right now, with plugins registered."""
    found = list(NATIVE_EXTENSIONS) + list(SVG_EXTENSIONS)
    for extensions, module_name, activate in _OPTIONAL:
        if _activate(module_name, activate):
            found.extend(extensions)
    return tuple(found)


def _activate(module_name: str | None, activate) -> bool:
    if module_name is None:
        return bool(activate())
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        return False
    activate(module)
    return True


DECODER_HINTS = {
    ".heic": "pip install pillow-heif",
    ".heif": "pip install pillow-heif",
    ".jxl": "pip install pillow-jxl-plugin",
    ".avif": "a Pillow build with AVIF support (pip install -U pillow)",
}


def decoder_hint(suffix: str) -> str | None:
    """How to enable a known-but-unavailable image type, if we can tell."""
    return DECODER_HINTS.get(suffix.lower())


def is_svg(suffix: str) -> bool:
    return suffix.lower() in SVG_EXTENSIONS


__all__ = ["Image", "decoder_hint", "is_svg", "supported_image_extensions"]
