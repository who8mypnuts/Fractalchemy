"""Disk-side halves of the save / open flows. No Qt: these run on the thread pool.

Each function does one complete file operation and returns what the GUI needs
to re-point the document afterwards.
"""

from __future__ import annotations

from pathlib import Path

from ..formats import FormatError, format_for, load_gradients
from ..model import Gradient


def load_entries(path: Path) -> list[Gradient]:
    """Every gradient in `path`.

    Raises:
        FormatError: If the file parses but holds no gradient (e.g. flames without palettes).
    """
    gradients = load_gradients(path)
    if not gradients:  # e.g. a flame file whose flames carry no palette
        raise FormatError(f"{path.name} contains no gradients")
    return gradients


def append_entry(gradient: Gradient, path: Path, source: tuple[Path, int] | None) -> int:
    """Add `gradient` to `path` (creating it if needed) and return the new entry's index.

    Args:
        gradient: What to write.
        path: Target file.
        source: (file, index) the gradient came from, so flame files can clone the fractal.

    Raises:
        ValueError: If the target format cannot take the entry.
    """
    fmt = format_for(path)
    if not (fmt.can_append if path.exists() else fmt.can_create):
        raise ValueError(f"Gradients cannot be added to {fmt.name} files")
    fmt.append(gradient, path, template=source)
    return len(fmt.names(path)) - 1


def write_file(gradient: Gradient, path: Path, source: tuple[Path, int] | None) -> tuple[int, str]:
    """'Save as new file', refusing to wipe an existing multi-gradient file.

    If `path` is the gradient's own source file it is saved into its slot; if it is
    another existing multi-gradient file the gradient is appended.

    Returns:
        (entry index to show, note for the status bar or '').

    Raises:
        ValueError: If the format cannot create files or take extra entries.
    """
    fmt = format_for(path)
    if path.exists() and fmt.multi_entry:
        if source is not None and path.resolve() == source[0].resolve():
            fmt.save(gradient, path, source[1])
            return source[1], f"{path.name} already holds this gradient — saved in place"
        if fmt.can_append:
            return append_entry(gradient, path, source), f"{path.name} exists — added '{gradient.name}' to it instead of replacing the file"
        raise ValueError(f"{path.name} exists and {fmt.name} files can't take extra gradients")
    if not fmt.can_create:
        raise ValueError(f"New {fmt.name} files cannot be created; choose another format")
    if path.exists():
        path.unlink()  # single-gradient file: the save dialog already confirmed the overwrite
    if fmt.can_append:
        fmt.append(gradient, path, template=source)
    else:
        fmt.save(gradient, path)
    return 0, ""
