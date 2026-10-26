"""Ultra Fractal `.ufr` fractal files: one gradient per layer.

Binary layout (reverse-engineered from UF6 files):

    0   "UltraFractal"            12 bytes magic
    12  version                   uint32 (1)
    16  text offset               uint32 (64)
    20  text length               uint32
    24  layer-info offset         uint32 (= text end)
    28  layer-info length         uint32
    32  pixel-cache offset        uint32 (zlib stream to EOF)
    36  width, height, layers     uint32 x3
    ...

The text is a UF parameter set; each `layer:` has a `gradient:` section. We
edit only that section and shift the two absolute offsets by the size delta,
leaving the cached render data untouched.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

from ..model import Gradient
from . import ufparams as uf
from .base import FormatError, GradientFormat
from .textfile import atomic_write_bytes, detect_newline, require_index

MAGIC = b"UltraFractal"
HEADER_SIZE = 64
_TEXT_OFFSET, _TEXT_LENGTH, _INFO_OFFSET, _CACHE_OFFSET = 16, 20, 24, 32


@dataclass
class _Ufr:
    header: bytearray
    text: str          # latin-1 decoded so untouched bytes round-trip exactly
    tail: bytes        # everything after the parameter text

    def encode(self) -> bytes:
        """Serialise with the header's length and offsets corrected for the text's new size."""
        body = self.text.encode("latin-1")
        header = bytearray(self.header)
        delta = len(body) - struct.unpack_from("<I", header, _TEXT_LENGTH)[0]
        struct.pack_into("<I", header, _TEXT_LENGTH, len(body))
        for field in (_INFO_OFFSET, _CACHE_OFFSET):
            struct.pack_into("<I", header, field, struct.unpack_from("<I", header, field)[0] + delta)
        return bytes(header) + body + self.tail


@dataclass(frozen=True)
class _Entry:
    name: str
    section: uf.Section


class UfrFormat(GradientFormat):
    """Reader/in-place writer for Ultra Fractal .ufr fractal files (one gradient per layer)."""
    name = "Ultra Fractal fractal"
    extensions = (".ufr",)
    can_save = True
    multi_entry = True

    def load(self, path: Path) -> list[Gradient]:
        """One gradient per layer, named after the layer caption."""
        doc = _read(path)
        gradients = [Gradient(e.name, uf.stops_from_tokens(uf.tokens(e.section.body))) for e in _entries(doc.text)]
        return [g for g in gradients if g.stops]

    def names(self, path: Path) -> list[str]:
        """Layer captions of every layer that has a gradient section."""
        return [e.name for e in _entries(_read(path).text)]

    def save(self, gradient: Gradient, path: Path, index: int = 0) -> None:
        """Rewrite the gradient section of layer `index`, keeping its other attributes."""
        doc = _read(path)
        section = require_index([e.section for e in _entries(doc.text)], index, path)
        kept = uf.other_tokens(uf.tokens(section.body))
        body = uf.wrap_tokens(kept + uf.stop_tokens(gradient.stops), detect_newline(doc.text))
        doc.text = doc.text[:section.body_start] + body + doc.text[section.body_end:]
        _write(path, doc)

    def rename(self, path: Path, index: int, name: str) -> None:
        """Set the caption of layer `index`."""
        doc = _read(path)
        section = require_index([s for s in uf.sections(doc.text) if s.name == "layer"], index, path)
        pairs = [(k, uf.quote(name) if k == "caption" else v) for k, v in uf.tokens(section.body)]
        if "caption" not in dict(pairs):
            pairs.insert(0, ("caption", uf.quote(name)))
        body = uf.wrap_tokens(pairs, detect_newline(doc.text))
        doc.text = doc.text[:section.body_start] + body + doc.text[section.body_end:]
        _write(path, doc)


# --- container --------------------------------------------------------------
def _read(path: Path) -> _Ufr:
    raw = path.read_bytes()
    if not raw.startswith(MAGIC) or len(raw) < HEADER_SIZE:
        raise FormatError(f"{path.name} is not an Ultra Fractal .ufr file")
    offset, length = struct.unpack_from("<II", raw, _TEXT_OFFSET)
    if offset != HEADER_SIZE or offset + length > len(raw):
        raise FormatError(f"{path.name} has an unexpected .ufr header")
    return _Ufr(bytearray(raw[:offset]), raw[offset:offset + length].decode("latin-1"), raw[offset + length:])


def _write(path: Path, doc: _Ufr) -> None:
    atomic_write_bytes(path, doc.encode())


# --- entries ----------------------------------------------------------------
def _entries(text: str) -> list[_Entry]:
    entries, caption, layer_no = [], None, 0
    for section in uf.sections(text):
        if section.name == "layer":
            layer_no += 1
            caption = uf.unquote(dict(uf.tokens(section.body)).get("caption", f"Layer {layer_no}"))
        elif section.name == "gradient":
            entries.append(_Entry(caption or f"Layer {layer_no or 1}", section))
            caption = None
    return entries
