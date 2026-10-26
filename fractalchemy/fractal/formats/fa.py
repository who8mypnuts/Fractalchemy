"""Fractalchemy's own `.fa` files: JSON, one document holding any number of flames.

    {"format": "fractalchemy", "version": 1, "flames": [ <Flame.to_dict()>, ... ]}

JSON keeps the format diff-friendly and trivially extensible: new keys are
ignored by older readers and missing keys take defaults (`Flame.from_dict`).
"""

from __future__ import annotations

import json
from pathlib import Path

from ..scene import Flame

FORMAT_ID = "fractalchemy"
FORMAT_VERSION = 1


class FaParseError(ValueError):
    """The file is not a Fractalchemy document."""


def parse_file(path: Path) -> list[Flame]:
    """Every flame in the document."""
    return [Flame.from_dict(d) for d in _document(path)["flames"]]


def flame_names(path: Path) -> list[str]:
    """Flame names without building the full objects."""
    return [d.get("name", "flame") for d in _document(path)["flames"]]


def write_file(flames: list[Flame], path: Path) -> None:
    """Write a document holding `flames` (replacing `path`)."""
    _write(path, {"format": FORMAT_ID, "version": FORMAT_VERSION, "flames": [f.to_dict() for f in flames]})


def append_flame(flame: Flame, path: Path) -> int:
    """Add a flame to the document (creating the file); returns its index."""
    doc = _document(path) if path.exists() else {"format": FORMAT_ID, "version": FORMAT_VERSION, "flames": []}
    doc["flames"].append(flame.to_dict())
    _write(path, doc)
    return len(doc["flames"]) - 1


def replace_flame(flame: Flame, path: Path, index: int) -> None:
    """Overwrite entry `index`."""
    doc = _document(path)
    _require(doc, index, path)
    doc["flames"][index] = flame.to_dict()
    _write(path, doc)


def remove_flame(path: Path, index: int) -> None:
    """Delete entry `index`."""
    doc = _document(path)
    _require(doc, index, path)
    del doc["flames"][index]
    _write(path, doc)


def rename_flame(path: Path, index: int, name: str) -> None:
    """Rename entry `index`."""
    doc = _document(path)
    _require(doc, index, path)
    doc["flames"][index]["name"] = name
    _write(path, doc)


def copy_flame(source: Path, index: int, target: Path) -> None:
    """Append entry `index` of `source` to `target` verbatim."""
    doc = _document(source)
    _require(doc, index, source)
    target_doc = _document(target) if target.exists() else {"format": FORMAT_ID, "version": FORMAT_VERSION, "flames": []}
    target_doc["flames"].append(doc["flames"][index])
    _write(target, target_doc)


# --- helpers ----------------------------------------------------------------
def _document(path: Path) -> dict:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise FaParseError(f"{path.name} is not a Fractalchemy document: {exc}") from exc
    if not isinstance(doc, dict) or doc.get("format") != FORMAT_ID or not isinstance(doc.get("flames"), list):
        raise FaParseError(f"{path.name} is not a Fractalchemy document")
    return doc


def _require(doc: dict, index: int, path: Path) -> None:
    if not 0 <= index < len(doc["flames"]):
        raise IndexError(f"{path.name} has no flame #{index + 1}")


def _write(path: Path, doc: dict) -> None:
    path.write_text(json.dumps(doc, indent=1), encoding="utf-8")
