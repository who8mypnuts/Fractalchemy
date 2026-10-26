"""Serialise library items for drag-and-drop and the clipboard."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QMimeData, QUrl

from .items import Kind, LibraryItem

MIME_TYPE = "application/x-fractalchemy-items"


def to_mime(items: list[LibraryItem], library: str = "") -> QMimeData:
    """Package items for drag-and-drop / the clipboard (plus file URLs for files, and plain text).

    `library` tags the payload so the gradient and fractal trees ignore each other's entries.
    """
    data = QMimeData()
    records = {"library": library,
               "items": [{"kind": i.kind.value, "path": str(i.path), "index": i.index, "name": i.name} for i in items]}
    data.setData(MIME_TYPE, json.dumps(records).encode("utf-8"))
    files = [i.path for i in items if i.kind == Kind.FILE]
    if files:
        data.setUrls([QUrl.fromLocalFile(str(p)) for p in files])  # lets files be dropped on the OS
    data.setText("\n".join(str(i.path) for i in items))
    return data


def from_mime(data: QMimeData, library: str | None = None) -> list[LibraryItem]:
    """Decode items from our own MIME type, or from file URLs dropped in from the desktop.

    With `library` given, payloads tagged for another library yield only their plain files.
    """
    if data.hasFormat(MIME_TYPE):
        records = json.loads(bytes(data.data(MIME_TYPE).data()).decode("utf-8"))
        items = [LibraryItem(Kind(r["kind"]), Path(r["path"]), r["index"], r["name"]) for r in records["items"]]
        if library is not None and records.get("library") != library:
            items = [i for i in items if i.kind == Kind.FILE]
        return items
    if data.hasUrls():  # files dragged in from the desktop / file manager
        return [LibraryItem(Kind.FILE, Path(u.toLocalFile()), name=Path(u.toLocalFile()).name)
                for u in data.urls() if u.isLocalFile()]
    return []
