"""The palettes inside Fractalchemy `.fa` documents, as gradients.

A `.fa` file is JSON: `{"format": "fractalchemy", "version": 1, "flames": [...]}` with each
flame carrying `"name"` and a `"palette"` of 256 hex triplets (see `fractal/formats/fa.py`,
which owns the full schema). Entry indices here are the flame indices, so the Gradient
Library and the Fractal Library agree on what `(path, index)` means.
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import config
from ..model import Gradient, hex_to_rgb, rgb_to_hex
from .base import FormatError, GradientFormat

FORMAT_ID = "fractalchemy"
FORMAT_VERSION = 1


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
        return [_gradient(f) for f in _document(path)["flames"]]

    def names(self, path: Path) -> list[str]:
        return [f.get("name", "flame") for f in _document(path)["flames"]]

    def save(self, gradient: Gradient, path: Path, index: int = 0) -> None:
        """Replace the palette of flame `index` (creating a one-flame document if `path` is new)."""
        if not path.exists():
            return self.append(gradient, path)
        doc = _document(path)
        _require(doc, index, path)
        doc["flames"][index]["palette"] = _hexes(gradient)
        _write(path, doc)

    def append(self, gradient: Gradient, path: Path, template: tuple[Path, int] | None = None) -> None:
        """Add a flame carrying the gradient; with a `.fa` template its transforms are cloned."""
        flame = {"name": gradient.name, "xforms": [{}]}
        if template is not None and self.matches(template[0]) and template[0].exists():
            source = _document(template[0])
            if 0 <= template[1] < len(source["flames"]):
                flame = dict(source["flames"][template[1]])
                flame["name"] = gradient.name
        flame["palette"] = _hexes(gradient)
        doc = _document(path) if path.exists() else _empty()
        doc["flames"].append(flame)
        _write(path, doc)

    def remove(self, path: Path, index: int) -> None:
        doc = _document(path)
        _require(doc, index, path)
        del doc["flames"][index]
        _write(path, doc)

    def rename(self, path: Path, index: int, name: str) -> None:
        doc = _document(path)
        _require(doc, index, path)
        doc["flames"][index]["name"] = name
        _write(path, doc)

    def copy_entry(self, source: Path, index: int, target: Path) -> None:
        doc = _document(source)
        _require(doc, index, source)
        target_doc = _document(target) if target.exists() else _empty()
        target_doc["flames"].append(doc["flames"][index])
        _write(target, target_doc)


def _gradient(flame: dict) -> Gradient:
    colors = [hex_to_rgb(h) for h in flame.get("palette", []) if isinstance(h, str) and len(h) == 6]
    return Gradient.from_colors(flame.get("name", "flame"), colors or [(0, 0, 0), (255, 255, 255)])


def _hexes(gradient: Gradient) -> list[str]:
    return [rgb_to_hex(c) for c in gradient.sample(config.FLAME_PALETTE_SIZE)]


def _empty() -> dict:
    return {"format": FORMAT_ID, "version": FORMAT_VERSION, "flames": []}


def _document(path: Path) -> dict:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        raise FormatError(f"{path.name} is not a Fractalchemy document: {exc}") from exc
    if not isinstance(doc, dict) or doc.get("format") != FORMAT_ID or not isinstance(doc.get("flames"), list):
        raise FormatError(f"{path.name} is not a Fractalchemy document")
    return doc


def _require(doc: dict, index: int, path: Path) -> None:
    if not 0 <= index < len(doc["flames"]):
        raise FormatError(f"{path.name} has no flame #{index + 1}")


def _write(path: Path, doc: dict) -> None:
    path.write_text(json.dumps(doc, indent=1), encoding="utf-8")
