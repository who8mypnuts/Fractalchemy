"""Contract every gradient file format implements."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..model import Gradient


class FormatError(Exception):
    """Raised when a file cannot be parsed as the expected format."""


class GradientFormat(ABC):
    name: str = ""
    extensions: tuple[str, ...] = ()
    # Capabilities. Defaults describe a read-only, single-gradient format.
    can_save: bool = False      # replace an existing entry in place
    can_create: bool = False    # write a brand-new file holding one gradient
    can_append: bool = False    # add an entry to an existing file
    can_remove: bool = False    # delete an entry from a file
    multi_entry: bool = False   # one file can hold several gradients

    def matches(self, path: Path) -> bool:
        return path.suffix.lower() in self.extensions

    def dialog_filter(self) -> str:
        patterns = " ".join(f"*{ext}" for ext in self.extensions)
        return f"{self.name} ({patterns})"

    # --- reading ------------------------------------------------------------
    @abstractmethod
    def load(self, path: Path) -> list[Gradient]:
        """Return every gradient found in the file, in file order."""

    def names(self, path: Path) -> list[str]:
        """Entry names only; formats override this with something cheaper than load()."""
        return [g.name for g in self.load(path)]

    # --- writing (only when can_save) ----------------------------------------
    def save(self, gradient: Gradient, path: Path, index: int = 0) -> None:
        """Replace entry `index` (creating the file if it doesn't exist and can_create)."""
        raise NotImplementedError(f"{self.name} files cannot be written")

    def append(self, gradient: Gradient, path: Path, template: tuple[Path, int] | None = None) -> None:
        """Add a gradient as a new entry (creating the file if needed).

        `template` = (file, index) of the entry the gradient came from; formats
        that carry more than colours (flames) clone that entry so nothing is lost.
        """
        raise NotImplementedError(f"{self.name} files cannot be written")

    def remove(self, path: Path, index: int) -> None:
        raise NotImplementedError(f"{self.name} files cannot be written")

    def rename(self, path: Path, index: int, name: str) -> None:
        raise NotImplementedError(f"{self.name} files cannot be written")

    def copy_entry(self, source: Path, index: int, target: Path) -> None:
        """Copy one entry verbatim between two files of this format
        (keeps data the Gradient model doesn't represent, e.g. xforms)."""
        self.append(self.load(source)[index], target)
