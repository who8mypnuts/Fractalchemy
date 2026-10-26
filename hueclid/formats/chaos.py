"""Chaotica `.chaos` worlds: each IFS has a `flam3_palette` table of 256 RGB floats (0..1)."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .. import config
from ..model import Gradient, clamp_channel
from .base import FormatError, GradientFormat
from .textfile import Span, TextFile, require_index, xml_attr

_IFS_TAGS = ("flam3_IFS", "IFS")
_IFS_SPAN = re.compile(r"<(flam3_IFS|IFS)\b.*?</\1>", re.DOTALL)
_IFS_NAME = re.compile(r'^(<(?:flam3_IFS|IFS)\b[^>]*?\bname=")[^"]*(")')
_PALETTE_VALUES = re.compile(r'(<table\s+name="flam3_palette"\s*>\s*<values>)(.*?)(</values>)', re.DOTALL)


class ChaosFormat(GradientFormat):
    """Reader/in-place writer for Chaotica worlds (one gradient per IFS with a palette)."""
    name = "Chaotica world"
    extensions = (".chaos",)
    can_save = True
    multi_entry = True

    def load(self, path: Path) -> list[Gradient]:
        """One gradient per IFS element that has a flam3_palette table."""
        gradients = [_gradient_from_ifs(ifs) for ifs in _ifs_elements(path)]
        return [g for g in gradients if g is not None]

    def names(self, path: Path) -> list[str]:
        """IFS names, in file order, for those that carry a palette."""
        return [_ifs_name(ifs) for ifs in _ifs_elements(path) if _palette_values(ifs) is not None]

    def save(self, gradient: Gradient, path: Path, index: int = 0) -> None:
        """Replace the palette values of IFS `index` with the gradient resampled to 256 colours."""
        doc, span = _open_ifs(path, index)
        values = " ".join(_fmt(c / 255.0) for rgb in gradient.sample(config.FLAME_PALETTE_SIZE) for c in rgb)
        replaced, count = _PALETTE_VALUES.subn(lambda m: f"{m.group(1)}{values}{m.group(3)}", doc.slice(span), count=1)
        if count == 0:
            raise FormatError(f"{path.name}: IFS {index} has no flam3_palette")
        doc.replace(span, replaced)
        doc.write()

    def rename(self, path: Path, index: int, name: str) -> None:
        """Set the `name` attribute of IFS `index`."""
        doc, span = _open_ifs(path, index)
        renamed = _IFS_NAME.sub(lambda m: f"{m.group(1)}{xml_attr(name)}{m.group(2)}", doc.slice(span), count=1)
        doc.replace(span, renamed)
        doc.write()


# --- helpers ----------------------------------------------------------------
def _open_ifs(path: Path, index: int) -> tuple[TextFile, Span]:
    """The file plus the text span of the `index`-th IFS that carries a palette."""
    doc = TextFile.read(path)
    spans = [m.span() for m in _IFS_SPAN.finditer(doc.text) if 'name="flam3_palette"' in m.group(0)]
    return doc, require_index(spans, index, path)


def _ifs_elements(path: Path) -> list[ET.Element]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise FormatError(f"{path.name} is not valid Chaotica XML: {exc}") from exc
    return [el for el in root.iter() if el.tag in _IFS_TAGS]


def _ifs_name(ifs: ET.Element) -> str:
    return ifs.get("name") or "IFS"


def _palette_values(ifs: ET.Element) -> str | None:
    for table in ifs.iter("table"):
        if table.get("name") == "flam3_palette":
            values = table.find("values")
            return values.text if values is not None else None
    return None


def _gradient_from_ifs(ifs: ET.Element) -> Gradient | None:
    text = _palette_values(ifs)
    if not text:
        return None
    floats = [float(v) for v in text.split()]
    colors = [tuple(clamp_channel(f * 255) for f in floats[i:i + 3]) for i in range(0, len(floats) - 2, 3)]
    return Gradient.from_colors(_ifs_name(ifs), colors) if colors else None


def _fmt(value: float) -> str:
    return f"{value:.8g}"
