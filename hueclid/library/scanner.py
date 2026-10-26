"""Walk a library root and describe the supported files in it (runs off the GUI thread)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..formats import FormatError, entry_names, format_for
from ..formats.registry import UnsupportedFormatError


@dataclass
class ScannedFile:
    path: Path
    names: list[str]   # gradient names inside (one for images / single-entry files)

    @property
    def multi(self) -> bool:
        return len(self.names) > 1


@dataclass
class ScannedDir:
    path: Path
    dirs: list["ScannedDir"] = field(default_factory=list)
    files: list[ScannedFile] = field(default_factory=list)

    def file_count(self) -> int:
        return len(self.files) + sum(d.file_count() for d in self.dirs)


def scan_directory(root: Path) -> ScannedDir:
    node = ScannedDir(root)
    try:
        children = sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except OSError:
        return node
    for child in children:
        if child.name.startswith("."):
            continue
        if child.is_dir():
            node.dirs.append(scan_directory(child))
        elif child.is_file():
            scanned = _scan_file(child)
            if scanned is not None:
                node.files.append(scanned)
    return node


def _scan_file(path: Path) -> ScannedFile | None:
    try:
        format_for(path)
    except UnsupportedFormatError:
        return None
    try:
        names = entry_names(path)
    except (FormatError, OSError, ValueError):
        names = []
    return ScannedFile(path, names) if names else None


def count_supported_files(root: Path) -> int:
    return scan_directory(root).file_count()
