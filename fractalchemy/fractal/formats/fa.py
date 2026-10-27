"""Fractalchemy's own `.fa` files: JSON, one document holding any number of flames.

The envelope lives in `formats.fa_document`; each entry is `Flame.to_dict()`. JSON keeps
the format diff-friendly and extensible: new keys are ignored by older readers and missing
keys take defaults (`Flame.from_dict`).
"""

from __future__ import annotations

from pathlib import Path

from ...formats.fa_document import (
    FORMAT_ID, FORMAT_VERSION, FaDocumentError, empty_document, read_document, read_or_new, require_entry,
    write_document,
)
from ..scene import Flame

FaParseError = FaDocumentError


def parse_file(path: Path) -> list[Flame]:
    """Every flame in the document."""
    return [Flame.from_dict(d) for d in read_document(path)["flames"]]


def flame_names(path: Path) -> list[str]:
    """Flame names without building the full objects."""
    return [d.get("name", "flame") for d in read_document(path)["flames"]]


def write_file(flames: list[Flame], path: Path) -> None:
    """Write a document holding `flames` (replacing `path`)."""
    doc = empty_document()
    doc["flames"] = [f.to_dict() for f in flames]
    write_document(path, doc)


def append_flame(flame: Flame, path: Path) -> int:
    """Add a flame to the document (creating the file); returns its index."""
    doc = read_or_new(path)
    doc["flames"].append(flame.to_dict())
    write_document(path, doc)
    return len(doc["flames"]) - 1


def replace_flame(flame: Flame, path: Path, index: int) -> None:
    """Overwrite entry `index`."""
    doc = read_document(path)
    require_entry(doc, index, path)
    doc["flames"][index] = flame.to_dict()
    write_document(path, doc)


def remove_flame(path: Path, index: int) -> None:
    """Delete entry `index`."""
    doc = read_document(path)
    require_entry(doc, index, path)
    del doc["flames"][index]
    write_document(path, doc)


def rename_flame(path: Path, index: int, name: str) -> None:
    """Rename entry `index`."""
    doc = read_document(path)
    require_entry(doc, index, path)
    doc["flames"][index]["name"] = name
    write_document(path, doc)


def copy_flame(source: Path, index: int, target: Path) -> None:
    """Append entry `index` of `source` to `target` verbatim."""
    doc = read_document(source)
    require_entry(doc, index, source)
    target_doc = read_or_new(target)
    target_doc["flames"].append(doc["flames"][index])
    write_document(target, target_doc)


__all__ = ["FORMAT_ID", "FORMAT_VERSION", "FaParseError", "parse_file", "flame_names", "write_file", "append_flame",
           "replace_flame", "remove_flame", "rename_flame", "copy_flame"]
