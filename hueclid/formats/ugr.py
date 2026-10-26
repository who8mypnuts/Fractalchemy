"""Ultra Fractal `.ugr` / `.gradient` files.

    name {
    gradient:
     title="name" smooth=no
     index=0 color=12106915
     ...
    }

`index` runs 0..399; `color` packs R | G<<8 | B<<16. A file may hold many
gradients one after another.
"""

from __future__ import annotations

import re
from pathlib import Path

from .. import config
from ..model import RGB, ColorStop, Gradient
from .base import FormatError, GradientFormat

_GRADIENT_BLOCK = re.compile(r"^\s*(?P<name>[^{\r\n]*?)\s*\{(?P<body>.*?)^\s*\}", re.DOTALL | re.MULTILINE)
_TITLE = re.compile(r'title="(?P<title>[^"]*)"')
_ENTRY = re.compile(r"index=(?P<index>\d+)\s+color=(?P<color>\d+)")


class UgrFormat(GradientFormat):
    name = "Ultra Fractal gradient"
    extensions = (".ugr", ".gradient")
    can_save = True

    def load(self, path: Path) -> list[Gradient]:
        text = path.read_text(encoding="utf-8", errors="replace")
        gradients = [_gradient_from_block(m) for m in _GRADIENT_BLOCK.finditer(text)]
        gradients = [g for g in gradients if g is not None]
        if not gradients:
            raise FormatError(f"{path.name} contains no gradients")
        return gradients

    def save(self, gradient: Gradient, path: Path) -> None:
        path.write_text(serialize(gradient), encoding="utf-8", newline="\r\n")


# --- decoding ---------------------------------------------------------------
def unpack_color(value: int) -> RGB:
    return value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF


def pack_color(rgb: RGB) -> int:
    r, g, b = rgb
    return r | (g << 8) | (b << 16)


def _gradient_from_block(match: re.Match) -> Gradient | None:
    body = match.group("body")
    if "gradient:" not in body:
        return None
    title = _TITLE.search(body)
    name = title.group("title") if title else match.group("name").strip()
    stops = [
        ColorStop(int(e.group("index")) / config.UGR_MAX_INDEX, unpack_color(int(e.group("color"))))
        for e in _ENTRY.finditer(body)
    ]
    return Gradient(name, stops) if stops else None


# --- encoding ---------------------------------------------------------------
def serialize(gradient: Gradient) -> str:
    lines = [f"{gradient.name} {{", "gradient:", f' title="{gradient.name}" smooth=no']
    lines += [
        f" index={round(s.position * config.UGR_MAX_INDEX)} color={pack_color(s.color)}"
        for s in gradient.stops
    ]
    lines += ["", "}", " ", ""]
    return "\n".join(lines)
