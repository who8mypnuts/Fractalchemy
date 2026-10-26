"""Which fractal file types exist and how to read / edit entries in them.

    load_flames(path)        -> list[Flame]
    flame_names(path)        -> list[str]        (cheap; used by the library scanner)
    fractal_format_for(path) -> FractalFormat    (entry operations for the library)
"""

from __future__ import annotations

from pathlib import Path

from ...formats.chaos import ChaosFormat as _GradientChaosFormat
from ...formats.flame import FlameFormat as _GradientFlameFormat, _append_text, _open as _open_flame_text
from ...formats.textfile import require_index
from ..scene import Flame
from . import chaos_world, fa, flame_xml
from .flame_xml import FlameParseError


class FractalFormat:
    """One file type that holds flames; capability flags say what the library may do to it."""
    name = ""
    extensions: tuple[str, ...] = ()
    can_append = False    # add a flame to an existing file / create a new one
    can_remove = False
    can_rename = False
    can_replace = False   # overwrite one entry in place
    multi_entry = True    # every fractal file type can hold several flames

    @property
    def can_create(self) -> bool:
        return self.can_append

    def matches(self, path: Path) -> bool:
        return path.suffix.lower() in self.extensions

    def dialog_filter(self) -> str:
        return f"{self.name} (" + " ".join(f"*{e}" for e in self.extensions) + ")"

    def load(self, path: Path) -> list[Flame]:
        raise NotImplementedError

    def names(self, path: Path) -> list[str]:
        return [f.name for f in self.load(path)]

    def write_file(self, flames: list[Flame], path: Path) -> None:
        """Write a whole new file holding `flames` (every format can)."""
        raise NotImplementedError(f"{self.name} files cannot be written")

    def append(self, flame: Flame, path: Path) -> int:
        raise NotImplementedError(f"{self.name} files cannot be written")

    def replace(self, flame: Flame, path: Path, index: int) -> None:
        raise NotImplementedError(f"{self.name} files cannot be written")

    def remove(self, path: Path, index: int) -> None:
        raise NotImplementedError(f"{self.name} files cannot be edited")

    def rename(self, path: Path, index: int, name: str) -> None:
        raise NotImplementedError(f"{self.name} files cannot be edited")

    def copy_entry(self, source: Path, index: int, target: Path) -> None:
        """Copy an entry verbatim between files of this format (keeps data the model doesn't hold)."""
        self.append(self.load(source)[index], target)


class FlameFileFormat(FractalFormat):
    """Apophysis / flam3 `.flame` (text edits are in place, so unknown data survives)."""
    name = "Flame"
    extensions = (".flame",)
    can_append = can_remove = can_rename = can_replace = True
    _text = _GradientFlameFormat()

    def load(self, path: Path) -> list[Flame]:
        return flame_xml.parse_file(path)

    def names(self, path: Path) -> list[str]:
        return flame_xml.flame_names(path)

    def write_file(self, flames: list[Flame], path: Path) -> None:
        path.write_text(flame_xml.flames_to_xml(flames, path.stem), encoding="utf-8")

    def append(self, flame: Flame, path: Path) -> int:
        _append_text(path, flame_xml.flame_to_xml(flame))
        return len(self.names(path)) - 1

    def replace(self, flame: Flame, path: Path, index: int) -> None:
        doc, spans = _open_flame_text(path)
        doc.replace(require_index(spans, index, path), flame_xml.flame_to_xml(flame))
        doc.write()

    def remove(self, path: Path, index: int) -> None:
        self._text.remove(path, index)

    def rename(self, path: Path, index: int, name: str) -> None:
        self._text.rename(path, index, name)

    def copy_entry(self, source: Path, index: int, target: Path) -> None:
        self._text.copy_entry(source, index, target)


class ChaosFileFormat(FractalFormat):
    """Chaotica worlds: readable, entries can be renamed."""
    name = "Chaotica world"
    extensions = (".chaos",)
    can_rename = True
    _text = _GradientChaosFormat()

    def load(self, path: Path) -> list[Flame]:
        return chaos_world.parse_file(path)

    def names(self, path: Path) -> list[str]:
        return chaos_world.flame_names(path)

    def write_file(self, flames: list[Flame], path: Path) -> None:
        path.write_text(chaos_world.flames_to_world(flames, path.stem), encoding="utf-8")

    def rename(self, path: Path, index: int, name: str) -> None:
        self._text.rename(path, index, name)


class FaFileFormat(FractalFormat):
    """Fractalchemy's own JSON documents."""
    name = "Fractalchemy"
    extensions = (".fa",)
    can_append = can_remove = can_rename = can_replace = True

    def load(self, path: Path) -> list[Flame]:
        return fa.parse_file(path)

    def names(self, path: Path) -> list[str]:
        return fa.flame_names(path)

    def write_file(self, flames: list[Flame], path: Path) -> None:
        fa.write_file(flames, path)

    def append(self, flame: Flame, path: Path) -> int:
        return fa.append_flame(flame, path)

    def replace(self, flame: Flame, path: Path, index: int) -> None:
        fa.replace_flame(flame, path, index)

    def remove(self, path: Path, index: int) -> None:
        fa.remove_flame(path, index)

    def rename(self, path: Path, index: int, name: str) -> None:
        fa.rename_flame(path, index, name)

    def copy_entry(self, source: Path, index: int, target: Path) -> None:
        fa.copy_flame(source, index, target)


FORMATS: tuple[FractalFormat, ...] = (FlameFileFormat(), FaFileFormat(), ChaosFileFormat())
DEFAULT_SAVE_FORMAT: FractalFormat = FORMATS[1]   # .fa
PARSE_ERRORS = (FlameParseError, chaos_world.ChaosParseError, fa.FaParseError)


class UnsupportedFractalFormat(ValueError):
    """No fractal format claims the path's extension."""


def fractal_format_for(path: Path | str) -> FractalFormat:
    """The format for `path`, by extension.

    Raises:
        UnsupportedFractalFormat: If none matches.
    """
    path = Path(path)
    for fmt in FORMATS:
        if fmt.matches(path):
            return fmt
    raise UnsupportedFractalFormat(f"No fractal reader for '{path.suffix or path.name}'")


def is_fractal_file(path: Path) -> bool:
    """True if some fractal format handles `path`."""
    return any(f.matches(Path(path)) for f in FORMATS)


def load_flames(path: Path | str) -> list[Flame]:
    """Every flame in the file."""
    return fractal_format_for(path).load(Path(path))


def load_flame(path: Path | str, index: int = 0) -> Flame:
    """One flame from the file.

    Raises:
        IndexError: If the file has no entry `index`.
    """
    flames = load_flames(path)
    if not 0 <= index < len(flames):
        raise IndexError(f"{Path(path).name} has no flame #{index + 1}")
    return flames[index]


def flame_names(path: Path | str) -> list[str]:
    """Names of the flames in a file (cheap)."""
    return fractal_format_for(path).names(Path(path))


def save_dialog_filter() -> str:
    """QFileDialog filter for saving: Fractalchemy first, then the others."""
    return ";;".join(f.dialog_filter() for f in FORMATS)


def open_dialog_filter() -> str:
    """QFileDialog filter for every readable fractal type."""
    all_patterns = " ".join(f"*{e}" for f in FORMATS for e in f.extensions)
    return ";;".join([f"All fractals ({all_patterns})", *(f.dialog_filter() for f in FORMATS)])


__all__ = [
    "FORMATS", "DEFAULT_SAVE_FORMAT", "PARSE_ERRORS", "FractalFormat", "UnsupportedFractalFormat",
    "fractal_format_for", "is_fractal_file", "load_flames", "load_flame", "flame_names", "open_dialog_filter",
    "save_dialog_filter",
]
