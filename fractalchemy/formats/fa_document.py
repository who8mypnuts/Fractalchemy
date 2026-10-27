"""The JSON envelope of Fractalchemy `.fa` documents, shared by the fractal and gradient readers.

    {"format": "fractalchemy", "version": 1, "flames": [ {...}, ... ]}

This module has no other dependencies, so both `fractal.formats.fa` (whole flames) and
`formats.fa_palette` (just the palettes) can build on it without import cycles.
"""

from __future__ import annotations

import json
from pathlib import Path

FORMAT_ID = "fractalchemy"
FORMAT_VERSION = 1


class FaDocumentError(ValueError):
    """The file is not a Fractalchemy document."""


def empty_document() -> dict:
    """A document with no flames."""
    return {"format": FORMAT_ID, "version": FORMAT_VERSION, "flames": []}


def read_document(path: Path) -> dict:
    """Parse and validate the envelope.

    Raises:
        FaDocumentError: If the file is not JSON or not a Fractalchemy document.
    """
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        raise FaDocumentError(f"{path.name} is not a Fractalchemy document: {exc}") from exc
    if not is_document(doc):
        raise FaDocumentError(f"{path.name} is not a Fractalchemy document")
    return doc


def read_or_new(path: Path) -> dict:
    """The document at `path`, or an empty one if the file does not exist yet."""
    return read_document(path) if path.exists() else empty_document()


def is_document(doc: object) -> bool:
    """True for a parsed object with our envelope and a list of flame dicts."""
    return (isinstance(doc, dict) and doc.get("format") == FORMAT_ID and isinstance(doc.get("flames"), list)
            and all(isinstance(f, dict) for f in doc["flames"]))


def write_document(path: Path, doc: dict) -> None:
    """Write the document as indented JSON."""
    path.write_text(json.dumps(doc, indent=1), encoding="utf-8")


def require_entry(doc: dict, index: int, path: Path) -> None:
    """Raises IndexError if the document has no flame `index`."""
    if not 0 <= index < len(doc["flames"]):
        raise IndexError(f"{path.name} has no flame #{index + 1}")
