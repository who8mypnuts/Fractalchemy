"""Apophysis / flam3 `.flame` files.

Each <flame> element carries a <palette count="256" format="RGB"> block of hex
triplets. Reading uses ElementTree; every write edits the text of one <flame>
span in place so xforms, formatting and line endings are left untouched.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .. import config
from ..model import Gradient, hex_to_rgb, rgb_to_hex
from .base import FormatError, GradientFormat
from .textfile import Span, TextFile, require_index

_FLAME_SPAN = re.compile(r"<flame\b.*?</flame>[ \t]*\r?\n?", re.DOTALL)
_PALETTE_BLOCK = re.compile(r"(<palette\b[^>]*>)(.*?)(</palette>)", re.DOTALL)
_NAME_ATTR = re.compile(r'(<flame\b[^>]*?\bname=")([^"]*)(")')
_HEX_TRIPLET = re.compile(r"[0-9A-Fa-f]{6}")
_FLAMES_CLOSE = re.compile(r"</Flames>", re.IGNORECASE)


class FlameFormat(GradientFormat):
    name = "Flame"
    extensions = (".flame",)
    can_save = True
    can_create = True
    can_append = True
    can_remove = True
    multi_entry = True

    # --- reading ------------------------------------------------------------
    def load(self, path: Path) -> list[Gradient]:
        gradients = [_gradient_from_flame(f) for f in _flame_elements(path)]
        return [g for g in gradients if g is not None]

    def names(self, path: Path) -> list[str]:
        return [f.get("name", "flame") for f in _flame_elements(path) if f.find("palette") is not None]

    # --- writing ------------------------------------------------------------
    def save(self, gradient: Gradient, path: Path, index: int = 0) -> None:
        if not path.exists():
            return self.append(gradient, path)
        doc, spans = _open(path)
        span = require_index(spans, index, path)
        doc.replace(span, _with_palette(doc.slice(span), gradient))
        doc.write()

    def append(self, gradient: Gradient, path: Path, template: tuple[Path, int] | None = None) -> None:
        """Add a <flame>. With a flame `template`, its xforms etc. are cloned under the new palette."""
        if template is not None and self.matches(template[0]) and template[0].exists():
            text = _cloned_flame(template[0], template[1], gradient)
        else:
            text = _minimal_flame(gradient)
        _append_text(path, text)

    def remove(self, path: Path, index: int) -> None:
        doc, spans = _open(path)
        doc.remove(require_index(spans, index, path))
        doc.write()

    def rename(self, path: Path, index: int, name: str) -> None:
        doc, spans = _open(path)
        span = require_index(spans, index, path)
        doc.replace(span, _renamed(doc.slice(span), name))
        doc.write()

    def copy_entry(self, source: Path, index: int, target: Path) -> None:
        doc, spans = _open(source)
        _append_text(target, doc.slice(require_index(spans, index, source)).rstrip() + "\n")


# --- parsing helpers --------------------------------------------------------
def _flame_elements(path: Path) -> list[ET.Element]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise FormatError(f"{path.name} is not valid flame XML: {exc}") from exc
    return [root] if root.tag == "flame" else root.findall("flame")


def _gradient_from_flame(flame: ET.Element) -> Gradient | None:
    palette = flame.find("palette")
    if palette is None or not palette.text:
        return None
    colors = [hex_to_rgb(h) for h in _HEX_TRIPLET.findall(palette.text)]
    return Gradient.from_colors(flame.get("name", "flame"), colors) if colors else None


def _open(path: Path) -> tuple[TextFile, list[Span]]:
    doc = TextFile.read(path)
    return doc, [m.span() for m in _FLAME_SPAN.finditer(doc.text)]


# --- text generation --------------------------------------------------------
def _palette_rows(gradient: Gradient) -> list[str]:
    hexes = [rgb_to_hex(c) for c in gradient.sample(config.FLAME_PALETTE_SIZE)]
    per_line = config.FLAME_COLORS_PER_LINE
    return ["".join(hexes[i:i + per_line]) for i in range(0, len(hexes), per_line)]


def _palette_element(gradient: Gradient) -> str:
    rows = "\n".join("      " + row for row in _palette_rows(gradient))
    return f'<palette count="{config.FLAME_PALETTE_SIZE}" format="RGB">\n{rows}\n   </palette>'


def _with_palette(flame_text: str, gradient: Gradient) -> str:
    new_text, count = _PALETTE_BLOCK.subn(lambda m: _palette_element(gradient), flame_text, count=1)
    if count == 0:
        raise FormatError("flame entry has no <palette> element to update")
    return new_text


def _renamed(flame_text: str, name: str) -> str:
    renamed, count = _NAME_ATTR.subn(lambda m: f"{m.group(1)}{_xml_attr(name)}{m.group(3)}", flame_text, count=1)
    return renamed if count else flame_text.replace("<flame", f'<flame name="{_xml_attr(name)}"', 1)


def _cloned_flame(template_path: Path, index: int, gradient: Gradient) -> str:
    """The template <flame> verbatim (xforms, camera, ...) with the new name and palette."""
    doc, spans = _open(template_path)
    element = doc.slice(require_index(spans, index, template_path)).rstrip() + "\n"
    return _with_palette(_renamed(element, gradient.name), gradient).replace(doc.newline, "\n")


def _minimal_flame(gradient: Gradient) -> str:
    return (
        f'<flame name="{_xml_attr(gradient.name)}" version="{config.APP_NAME}" size="800 600" '
        'center="0 0" scale="200" background="0 0 0" brightness="4" gamma="4">\n'
        '   <xform weight="0.5" color="0" linear="1" coefs="1 0 0 1 0 0" />\n'
        f"   {_palette_element(gradient)}\n"
        "</flame>\n"
    )


def _append_text(path: Path, flame_text: str) -> None:
    """Add a <flame> to a file, wrapping a bare single-flame file in <Flames> first."""
    if not path.exists():
        TextFile.empty(path, "\n").write()
        doc = TextFile.read(path)
        doc.insert(0, flame_text)
        return doc.write()
    doc = TextFile.read(path)
    close = _FLAMES_CLOSE.search(doc.text)
    if close is not None:
        doc.insert(close.start(), flame_text)
    else:
        body = doc.text.rstrip() + doc.newline if doc.text.strip() else ""
        doc.text = doc.nl(f'<Flames name="{_xml_attr(path.stem)}">\n') + body
        doc.insert(len(doc.text), flame_text + "</Flames>\n")
    doc.write()


def _xml_attr(text: str) -> str:
    return text.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
