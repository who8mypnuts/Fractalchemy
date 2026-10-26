"""Apophysis / flam3 `.flame` files.

Each <flame> element carries a <palette count="256" format="RGB"> block of hex
triplets. Reading uses ElementTree; writing swaps the palette text in place so
the rest of an existing file (xforms, formatting, line endings) is untouched.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .. import config
from ..model import Gradient, hex_to_rgb, rgb_to_hex
from .base import FormatError, GradientFormat

_PALETTE_BLOCK = re.compile(r"(<palette\b[^>]*>)(.*?)(</palette>)", re.DOTALL)
_HEX_TRIPLET = re.compile(r"[0-9A-Fa-f]{6}")


class FlameFormat(GradientFormat):
    name = "Flame"
    extensions = (".flame",)
    can_save = True

    # --- reading ------------------------------------------------------------
    def load(self, path: Path) -> list[Gradient]:
        root = _parse_xml(path)
        flames = [root] if root.tag == "flame" else root.findall("flame")
        gradients = [_gradient_from_flame(flame) for flame in flames]
        return [g for g in gradients if g is not None]

    # --- writing ------------------------------------------------------------
    def save(self, gradient: Gradient, path: Path) -> None:
        block = _palette_block(gradient)
        if path.exists():
            _replace_first_palette(path, block)
        else:
            path.write_text(_minimal_flame(gradient.name, block), encoding="utf-8")


# --- helpers ----------------------------------------------------------------
def _parse_xml(path: Path) -> ET.Element:
    try:
        return ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise FormatError(f"{path.name} is not valid flame XML: {exc}") from exc


def _gradient_from_flame(flame: ET.Element) -> Gradient | None:
    palette = flame.find("palette")
    if palette is None or not palette.text:
        return None
    colors = [hex_to_rgb(h) for h in _HEX_TRIPLET.findall(palette.text)]
    if not colors:
        return None
    return Gradient.from_colors(flame.get("name", "flame"), colors)


def _palette_rows(gradient: Gradient) -> list[str]:
    hexes = [rgb_to_hex(c) for c in gradient.sample(config.FLAME_PALETTE_SIZE)]
    per_line = config.FLAME_COLORS_PER_LINE
    return ["".join(hexes[i:i + per_line]) for i in range(0, len(hexes), per_line)]


def _palette_block(gradient: Gradient, newline: str = "\n") -> str:
    body = newline.join("      " + row for row in _palette_rows(gradient))
    return f"{newline}{body}{newline}   "


def _replace_first_palette(path: Path, block: str) -> None:
    raw = path.read_bytes()
    newline = "\r\n" if b"\r\n" in raw else "\n"
    text = raw.decode("utf-8")
    block = block.replace("\n", newline)
    tag = '<palette count="%d" format="RGB">' % config.FLAME_PALETTE_SIZE
    new_text, count = _PALETTE_BLOCK.subn(lambda m: f"{tag}{block}{m.group(3)}", text, count=1)
    if count == 0:
        raise FormatError(f"{path.name} has no <palette> element to update")
    path.write_bytes(new_text.encode("utf-8"))


def _minimal_flame(name: str, block: str) -> str:
    return (
        f'<flame name="{_xml_attr(name)}" version="{config.APP_NAME}" size="800 600" '
        'center="0 0" scale="200" background="0 0 0" brightness="4" gamma="4">\n'
        '   <xform weight="0.5" color="0" linear="1" coefs="1 0 0 1 0 0" />\n'
        f'   <palette count="{config.FLAME_PALETTE_SIZE}" format="RGB">{block}</palette>\n'
        "</flame>\n"
    )


def _xml_attr(text: str) -> str:
    return text.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
