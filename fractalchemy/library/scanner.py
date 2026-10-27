"""Walk a library root and describe the supported files in it (runs off the GUI thread)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .catalog import Catalog


@dataclass
class ScannedFile:
    """A supported file found during a scan.

    Attributes:
        path: The file.
        names: Entry names inside it (one entry for single-entry types).
    """
    path: Path
    names: list[str]

    @property
    def multi(self) -> bool:
        """True when the file holds more than one entry."""
        return len(self.names) > 1


@dataclass
class ScannedDir:
    """A folder found during a scan, with its supported contents.

    Attributes:
        path: The folder.
        dirs: Sub-folders (all of them, even empty ones).
        files: Supported files directly inside.
    """
    path: Path
    dirs: list["ScannedDir"] = field(default_factory=list)
    files: list[ScannedFile] = field(default_factory=list)

    def file_count(self) -> int:
        """Supported files in this folder and every sub-folder."""
        return len(self.files) + sum(d.file_count() for d in self.dirs)


def scan_directory(root: Path, catalog: Catalog) -> ScannedDir:
    """Walk `root` and describe every file `catalog` supports (slow: run on a worker thread).

    Hidden entries and directory symlinks are skipped; unreadable folders yield
    an empty node rather than an error.
    """
    node = ScannedDir(root)
    try:
        children = sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except OSError:
        return node
    for child in children:
        if child.name.startswith(".") or (child.is_symlink() and child.is_dir()):
            continue  # hidden entries; directory symlinks could loop back into the tree
        if child.is_dir():
            node.dirs.append(scan_directory(child, catalog))
        elif child.is_file():
            scanned = _scan_file(child, catalog)
            if scanned is not None:
                node.files.append(scanned)
    return node


def scan_file(path: Path, catalog: Catalog) -> ScannedFile | None:
    """Describe one file (None if the catalog does not support it or it holds no entries)."""
    return _scan_file(path, catalog)


def _scan_file(path: Path, catalog: Catalog) -> ScannedFile | None:
    if not catalog.matches(path):
        return None
    try:
        names = catalog.entry_names(path)
    except Exception:  # noqa: BLE001 - unreadable or malformed: list nothing rather than abort the scan
        names = []
    return ScannedFile(path, names) if names else None


def count_supported_files(root: Path, catalog: Catalog) -> int:
    """Number of supported files under `root`, recursively."""
    return scan_directory(root, catalog).file_count()
