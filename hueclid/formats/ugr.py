"""Ultra Fractal `.ugr` / `.gradient` files.

    name {
    gradient:
     title="name" smooth=no
     index=0 color=12106915
     ...
    }

`index` runs 0..399; `color` packs R | G<<8 | B<<16. A file may hold many
gradients one after another; each is edited as a text span so any extras
Ultra Fractal wrote (opacity curves, rotation...) survive untouched.
"""

from __future__ import annotations

import re
from pathlib import Path

from .. import config
from ..model import RGB, ColorStop, Gradient
from .base import FormatError, GradientFormat
from .textfile import Span, TextFile, require_index

_GRADIENT_BLOCK = re.compile(
    r"^[ \t]*(?P<name>[^{\r\n]*?)[ \t]*\{(?P<body>.*?)^[ \t]*\}[ \t]*\r?\n?(?:[ \t]+\r?\n)?",
    re.DOTALL | re.MULTILINE,
)
_TITLE = re.compile(r'title="(?P<title>[^"]*)"')
_ENTRY = re.compile(r"index=(?P<index>\d+)\s+color=(?P<color>\d+)")


class UgrFormat(GradientFormat):
    name = "Ultra Fractal gradient"
    extensions = (".ugr", ".gradient")
    can_save = True
    can_create = True
    can_append = True
    can_remove = True
    multi_entry = True

    # --- reading ------------------------------------------------------------
    def load(self, path: Path) -> list[Gradient]:
        gradients = [_gradient_from_block(m) for m in _blocks(path)]
        gradients = [g for g in gradients if g is not None]
        if not gradients:
            raise FormatError(f"{path.name} contains no gradients")
        return gradients

    def names(self, path: Path) -> list[str]:
        return [_block_name(m) for m in _blocks(path) if "gradient:" in m.group("body")]

    # --- writing ------------------------------------------------------------
    def save(self, gradient: Gradient, path: Path, index: int = 0) -> None:
        if not path.exists():
            return self.append(gradient, path)
        doc, spans = _open(path)
        doc.replace(require_index(spans, index, path), serialize(gradient))
        doc.write()

    def append(self, gradient: Gradient, path: Path, template: tuple[Path, int] | None = None) -> None:
        _append_text(path, serialize(gradient))

    def remove(self, path: Path, index: int) -> None:
        doc, spans = _open(path)
        doc.remove(require_index(spans, index, path))
        doc.write()

    def rename(self, path: Path, index: int, name: str) -> None:
        doc, spans = _open(path)
        span = require_index(spans, index, path)
        block = doc.slice(span)
        block = re.sub(r"^[ \t]*[^{\r\n]*?[ \t]*\{", f"{name} {{", block, count=1)
        block = _TITLE.sub(f'title="{name}"', block, count=1)
        doc.replace(span, block)
        doc.write()

    def copy_entry(self, source: Path, index: int, target: Path) -> None:
        doc, spans = _open(source)
        _append_text(target, doc.slice(require_index(spans, index, source)))


# --- decoding ---------------------------------------------------------------
def unpack_color(value: int) -> RGB:
    return value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF


def pack_color(rgb: RGB) -> int:
    r, g, b = rgb
    return r | (g << 8) | (b << 16)


def _blocks(path: Path) -> list[re.Match]:
    return list(_GRADIENT_BLOCK.finditer(path.read_text(encoding="utf-8", errors="replace")))


def _open(path: Path) -> tuple[TextFile, list[Span]]:
    doc = TextFile.read(path)
    return doc, [m.span() for m in _GRADIENT_BLOCK.finditer(doc.text) if "gradient:" in m.group("body")]


def _block_name(match: re.Match) -> str:
    title = _TITLE.search(match.group("body"))
    return title.group("title") if title else match.group("name").strip()


def _gradient_from_block(match: re.Match) -> Gradient | None:
    body = match.group("body")
    if "gradient:" not in body:
        return None
    stops = [
        ColorStop(int(e.group("index")) / config.UGR_MAX_INDEX, unpack_color(int(e.group("color"))))
        for e in _ENTRY.finditer(body)
    ]
    return Gradient(_block_name(match), stops) if stops else None


# --- encoding ---------------------------------------------------------------
def serialize(gradient: Gradient) -> str:
    lines = [f"{gradient.name} {{", "gradient:", f' title="{gradient.name}" smooth=no']
    lines += [
        f" index={round(s.position * config.UGR_MAX_INDEX)} color={pack_color(s.color)}"
        for s in gradient.stops
    ]
    lines += ["", "}", " ", ""]
    return "\n".join(lines)


def _append_text(path: Path, block: str) -> None:
    doc = TextFile.read(path) if path.exists() else TextFile.empty(path)
    if doc.text and not doc.text.endswith(("\n", "\r\n")):
        doc.insert(len(doc.text), "\n")
    doc.insert(len(doc.text), block.rstrip() + "\n \n")
    doc.write()
