"""What a tree row refers to. Shared by model, menus, drag payloads and controller."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Kind(str, Enum):
    """What a library tree row represents."""
    ROOT = "root"          # a directory the user added to the library
    DIR = "dir"            # a sub-directory
    FILE = "file"          # a supported file (image / flame / ugr / fa ...)
    ENTRY = "entry"        # one named entry inside a multi-entry file (a gradient, a flame)
    SEPARATOR = "separator"   # the line under the temporary "opened file" area (not an item you can act on)


@dataclass(frozen=True)
class LibraryItem:
    """Identity of one tree row, shared by the model, menus, drag payloads and controller.

    Attributes:
        kind: Root folder, sub-folder, file, or an entry inside a file.
        path: The folder or file on disk.
        index: Entry index inside the file for ENTRY rows; 0 otherwise.
        name: Display text.
        temporary: True for the rows of the opened file shown above the library (not one of its folders).
    """
    kind: Kind
    path: Path
    index: int = 0          # entry index for ENTRY, else 0
    name: str = ""
    temporary: bool = False

    @property
    def is_directory(self) -> bool:
        """True for root and sub-folder rows."""
        return self.kind in (Kind.ROOT, Kind.DIR)

    @property
    def opens_entry(self) -> bool:
        """True for rows that load something when chosen (files and entries)."""
        return self.kind in (Kind.FILE, Kind.ENTRY)

    @property
    def directory(self) -> Path:
        """The folder this item lives in (itself for folders)."""
        return self.path if self.is_directory else self.path.parent
