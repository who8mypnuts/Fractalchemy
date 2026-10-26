"""What a tree row refers to. Shared by model, menus, drag payloads and controller."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Kind(str, Enum):
    ROOT = "root"          # a directory the user added to the library
    DIR = "dir"            # a sub-directory
    FILE = "file"          # a supported file (image / flame / ugr)
    GRADIENT = "gradient"  # one named entry inside a multi-gradient file


@dataclass(frozen=True)
class LibraryItem:
    kind: Kind
    path: Path
    index: int = 0          # entry index for GRADIENT, else 0
    name: str = ""

    @property
    def is_directory(self) -> bool:
        return self.kind in (Kind.ROOT, Kind.DIR)

    @property
    def shows_gradient(self) -> bool:
        return self.kind in (Kind.FILE, Kind.GRADIENT)

    @property
    def directory(self) -> Path:
        return self.path if self.is_directory else self.path.parent
