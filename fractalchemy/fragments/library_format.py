"""What the library pane needs to know about fragment files: one entry per file, copied as text.

A `.frag` / `.fafrag` holds exactly one fragment, named after the file; dropping one on a folder copies the file
(`entry_to_new_file`), nothing can be appended or removed inside it. Files inside the bundled library are read-only.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .examples import LIBRARY_DIR


def is_bundled_path(path: Path) -> bool:
    try:
        Path(path).resolve().relative_to(LIBRARY_DIR.resolve())
        return True
    except ValueError:
        return False


def fragment_names(path: Path) -> list[str]:
    """The one entry of a fragment file: its stem (the library lists the file itself)."""
    return [Path(path).stem]


class FragmentFormat:
    """The `EntryFormat` of fragment files."""
    name = "fragment"
    can_append = False
    can_remove = False
    multi_entry = False
    can_rename = False

    def names(self, path: Path) -> list[str]:
        return fragment_names(path)

    def copy_entry(self, source: Path, index: int, target: Path) -> None:
        """Copy the fragment file to `target` (a new file; fragments hold one entry)."""
        if is_bundled_path(target):
            raise ValueError("The bundled example library is read-only")
        shutil.copyfile(source, target)

    def remove(self, path: Path, index: int) -> None:
        raise ValueError("A fragment file holds one fragment; delete the file instead")

    def rename(self, path: Path, index: int, name: str) -> None:
        raise ValueError("Rename the fragment file instead")


__all__ = ["FragmentFormat", "fragment_names", "is_bundled_path"]
