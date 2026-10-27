"""The palettes inside Fractalchemy `.fa` documents, as gradients.

Each flame in the document carries `"name"` and a `"palette"` of 256 hex triplets (see
`fractal/formats/fa.py` for the full flame schema). Entry indices here are the flame
indices, so the Gradient Library and the Fractal Library agree on what `(path, index)` means.
"""

from __future__ import annotations

from pathlib import Path

from .. import config
from ..model import Gradient, hex_to_rgb, rgb_to_hex
from .base import FormatError, GradientFormat
from .fa_document import FaDocumentError, read_document, read_or_new, require_entry, write_document


class FaPaletteFormat(GradientFormat):
    """Reader/writer for the palettes of Fractalchemy documents (one gradient per flame)."""
    name = "Fractalchemy"
    extensions = (".fa",)
    can_save = True
    can_create = True
    can_append = True
    can_remove = True
    multi_entry = True

    def load(self, path: Path) -> list[Gradient]:
        return [_gradient(f) for f in _read(path)["flames"]]

    def names(self, path: Path) -> list[str]:
        return [f.get("name", "flame") for f in _read(path)["flames"]]

    def save(self, gradient: Gradient, path: Path, index: int = 0) -> None:
        """Replace the palette of flame `index` (creating a one-flame document if `path` is new)."""
        if not path.exists():
            return self.append(gradient, path)
        doc = _read(path)
        _require(doc, index, path)
        doc["flames"][index]["palette"] = _hexes(gradient)
        write_document(path, doc)

    def append(self, gradient: Gradient, path: Path, template: tuple[Path, int] | None = None) -> None:
        """Add a flame carrying the gradient; with a `.fa` template its transforms are cloned."""
        flame = {"name": gradient.name, "xforms": [{}]}   # `{}` is a default linear xform for Flame.from_dict
        if template is not None and self.matches(template[0]) and template[0].exists():
            source = _read(template[0])
            if 0 <= template[1] < len(source["flames"]):
                flame = dict(source["flames"][template[1]])
                flame["name"] = gradient.name
        flame["palette"] = _hexes(gradient)
        doc = read_or_new(path)
        doc["flames"].append(flame)
        write_document(path, doc)

    def remove(self, path: Path, index: int) -> None:
        doc = _read(path)
        _require(doc, index, path)
        del doc["flames"][index]
        write_document(path, doc)

    def rename(self, path: Path, index: int, name: str) -> None:
        doc = _read(path)
        _require(doc, index, path)
        doc["flames"][index]["name"] = name
        write_document(path, doc)

    def copy_entry(self, source: Path, index: int, target: Path) -> None:
        doc = _read(source)
        _require(doc, index, source)
        target_doc = read_or_new(target)
        target_doc["flames"].append(doc["flames"][index])
        write_document(target, target_doc)


def _read(path: Path) -> dict:
    """The document, with envelope errors reported as the gradient layer's FormatError."""
    try:
        return read_document(path)
    except FaDocumentError as exc:
        raise FormatError(str(exc)) from exc


def _require(doc: dict, index: int, path: Path) -> None:
    try:
        require_entry(doc, index, path)
    except IndexError as exc:
        raise FormatError(str(exc)) from exc


def _gradient(flame: dict) -> Gradient:
    colors = [hex_to_rgb(h) for h in flame.get("palette", []) if isinstance(h, str) and len(h) == 6]
    return Gradient.from_colors(flame.get("name", "flame"), colors or [(0, 0, 0), (255, 255, 255)])


def _hexes(gradient: Gradient) -> list[str]:
    return [rgb_to_hex(c) for c in gradient.sample(config.FLAME_PALETTE_SIZE)]
