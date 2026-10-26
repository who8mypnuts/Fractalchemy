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
    can_save: bool = False

    def matches(self, path: Path) -> bool:
        return path.suffix.lower() in self.extensions

    def dialog_filter(self) -> str:
        patterns = " ".join(f"*{ext}" for ext in self.extensions)
        return f"{self.name} ({patterns})"

    @abstractmethod
    def load(self, path: Path) -> list[Gradient]:
        """Return every gradient found in the file, in file order."""

    def save(self, gradient: Gradient, path: Path) -> None:
        raise NotImplementedError(f"{self.name} files cannot be written")
