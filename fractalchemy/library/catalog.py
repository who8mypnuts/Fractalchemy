"""What a library holds: which files count, how their entries are listed and edited.

The library machinery (scanner, model, tree, controller, menus) is generic; a
`Catalog` plugs in the file-type knowledge. Two exist: gradients (for the
Gradient Library window) and fractals (for the main window's Fractal Library).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol


class EntryFormat(Protocol):
    """The slice of a file format the library needs for entry operations."""
    name: str
    can_append: bool
    can_remove: bool
    multi_entry: bool

    def names(self, path: Path) -> list[str]: ...
    def copy_entry(self, source: Path, index: int, target: Path) -> None: ...
    def remove(self, path: Path, index: int) -> None: ...
    def rename(self, path: Path, index: int, name: str) -> None: ...


@dataclass(frozen=True)
class Catalog:
    """File-type knowledge for one library.

    Attributes:
        key: Identifies the library in QSettings and drag payloads.
        title: Human name ("Gradient Library").
        entry_label: What an entry is called in messages ("gradient" / "fractal").
        matches: True for files this library lists.
        entry_names: Names of the entries in a file; may raise on unreadable files.
        format_for: Format object for entry operations; raises for unsupported paths.
        cross_copy: Copies entry `index` of `source` into `target` when their formats differ
            (gradients convert; fractals refuse). Signature `(source, index, target)`.
        new_file_suffix: Extension for files created by dropping an entry on a folder.
    """
    key: str
    title: str
    entry_label: str
    matches: Callable[[Path], bool]
    entry_names: Callable[[Path], list[str]]
    format_for: Callable[[Path], EntryFormat]
    cross_copy: Callable[[Path, int, Path], None]
    new_file_suffix: str

    @property
    def roots_key(self) -> str:
        """QSettings key of the folder list."""
        return f"{self.key}/roots"


def _gradient_catalog() -> Catalog:
    from ..formats import DEFAULT_SAVE_FORMAT, entry_names, format_for, load_gradients
    from ..formats.registry import UnsupportedFormatError

    def matches(path: Path) -> bool:
        try:
            format_for(path)
            return True
        except UnsupportedFormatError:
            return False

    def cross_copy(source: Path, index: int, target: Path) -> None:
        format_for(target).append(load_gradients(source)[index], target)

    return Catalog("library", "Gradient Library", "gradient", matches, entry_names, format_for, cross_copy,
                   DEFAULT_SAVE_FORMAT.extensions[0])


def _fractal_catalog() -> Catalog:
    from ..fractal.formats import DEFAULT_SAVE_FORMAT, flame_names, fractal_format_for, is_fractal_file

    def cross_copy(source: Path, index: int, target: Path) -> None:
        raise ValueError(f"Fractals can only be copied between files of the same type ({source.suffix} → {target.suffix})")

    return Catalog("fractal_library", "Fractal Library", "fractal", is_fractal_file, flame_names, fractal_format_for,
                   cross_copy, DEFAULT_SAVE_FORMAT.extensions[0])


GRADIENT_CATALOG = _gradient_catalog()
FRACTAL_CATALOG = _fractal_catalog()
