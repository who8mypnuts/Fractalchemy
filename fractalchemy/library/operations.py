"""File-system and entry operations behind the library's menus and drops.

Plain functions, no widgets: they run on a worker thread and return a short
status string. Errors surface as exceptions for the controller to report.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import QFile

from .catalog import Catalog
from .items import Kind, LibraryItem


# --- files ------------------------------------------------------------------
def unique_path(candidate: Path) -> Path:
    """`name.ext` → `name copy.ext`, `name copy 2.ext`, ... until unused."""
    if not candidate.exists():
        return candidate
    stem, suffix, parent = candidate.stem, candidate.suffix, candidate.parent
    n = 1
    while True:
        label = " copy" if n == 1 else f" copy {n}"
        path = parent / f"{stem}{label}{suffix}"
        if not path.exists():
            return path
        n += 1


def duplicate_file(path: Path) -> str:
    """Copy a file next to itself as 'name copy.ext'."""
    target = unique_path(path)
    shutil.copy2(path, target)
    return f"Duplicated to {target.name}"


def delete_path(path: Path) -> str:
    """Move a file or folder to the trash, deleting outright if the platform has no trash."""
    if QFile.moveToTrash(str(path)):
        return f"Moved {path.name} to the trash"
    shutil.rmtree(path) if path.is_dir() else path.unlink()
    return f"Deleted {path.name}"


def rename_path(path: Path, new_name: str) -> str:
    """Rename within the same folder.

    Raises:
        FileExistsError: If `new_name` is taken.
    """
    target = path.with_name(new_name)
    if target.exists():
        raise FileExistsError(f"{new_name} already exists")
    path.rename(target)
    return f"Renamed to {new_name}"


def create_folder(parent: Path, name: str) -> str:
    """Create `parent/name`.

    Raises:
        FileExistsError: If it already exists.
    """
    (parent / name).mkdir(parents=False, exist_ok=False)
    return f"Created folder {name}"


def copy_files(paths: list[Path], dest_dir: Path) -> str:
    """Copy files into `dest_dir`, suffixing names that collide."""
    for path in paths:
        shutil.copy2(path, unique_path(dest_dir / path.name))
    return f"Copied {len(paths)} file(s) to {dest_dir.name}"


def move_files(paths: list[Path], dest_dir: Path) -> str:
    """Move files into `dest_dir`, suffixing names that collide; files already there are left alone."""
    moved = 0
    for path in paths:
        if path.parent != dest_dir:
            shutil.move(str(path), str(unique_path(dest_dir / path.name)))
            moved += 1
    return f"Moved {moved} file(s) to {dest_dir.name}"


# --- entries (gradients / flames, per the catalog) ---------------------------
def transfer_entry(catalog: Catalog, source: Path, index: int, target: Path, move: bool) -> str:
    """Append entry `index` of `source` to `target`; optionally remove it from source."""
    label = catalog.entry_label
    src_fmt, dst_fmt = catalog.format_for(source), catalog.format_for(target)
    if target.exists() and not dst_fmt.can_append:
        raise ValueError(f"{label.capitalize()}s cannot be added to existing {dst_fmt.name} files")
    if not target.exists() and not getattr(dst_fmt, "can_create", dst_fmt.can_append):
        raise ValueError(f"{label.capitalize()}s cannot be saved as new {dst_fmt.name} files")
    if move and not src_fmt.can_remove:
        raise ValueError(f"Hold Ctrl to copy: {label}s can't be removed from {src_fmt.name} files")
    if move and len(src_fmt.names(source)) <= 1:
        raise ValueError(f"Hold Ctrl to copy: a file must keep at least one {label}")
    if src_fmt is dst_fmt:
        dst_fmt.copy_entry(source, index, target)
    else:
        catalog.cross_copy(source, index, target)
    if move:
        src_fmt.remove(source, index)
    return f"{'Moved' if move else 'Copied'} {label} to {target.name}"


def entry_to_new_file(catalog: Catalog, source: Path, index: int, dest_dir: Path) -> str:
    """Create a new file in `dest_dir` (named after the entry) holding entry `index` of `source`."""
    fmt = catalog.format_for(source)
    name = fmt.names(source)[index] if fmt.multi_entry else source.stem
    target = unique_path(dest_dir / f"{_safe_filename(name, catalog.entry_label)}{catalog.new_file_suffix}")
    transfer_entry(catalog, source, index, target, move=False)
    return f"Created {target.name}"


def duplicate_entry(catalog: Catalog, path: Path, index: int) -> str:
    """Append a verbatim copy of entry `index` to its own file.

    Raises:
        ValueError: If the format cannot hold extra entries.
    """
    fmt = catalog.format_for(path)
    if not fmt.can_append:
        raise ValueError(f"{fmt.name} files can't hold extra {catalog.entry_label}s")
    fmt.copy_entry(path, index, path)
    return f"Duplicated {catalog.entry_label}"


def delete_entry(catalog: Catalog, path: Path, index: int) -> str:
    """Remove entry `index` from its file.

    Raises:
        ValueError: If the format forbids removal or only one entry would remain.
    """
    fmt = catalog.format_for(path)
    if not fmt.can_remove:
        raise ValueError(f"{catalog.entry_label.capitalize()}s can't be removed from {fmt.name} files")
    if len(fmt.names(path)) <= 1:
        raise ValueError(f"A file must keep at least one {catalog.entry_label}; delete the file instead")
    fmt.remove(path, index)
    return f"Deleted {catalog.entry_label}"


def rename_entry(catalog: Catalog, path: Path, index: int, name: str) -> str:
    """Rename entry `index` inside its file."""
    fmt = catalog.format_for(path)
    if not getattr(fmt, "can_rename", True):
        raise ValueError(f"{catalog.entry_label.capitalize()}s in {fmt.name} files can't be renamed")
    fmt.rename(path, index, name)
    return f"Renamed {catalog.entry_label} to {name}"


# --- dispatch helpers for drops / paste ------------------------------------
def drop_items(catalog: Catalog, items: list[LibraryItem], target: LibraryItem, move: bool) -> str:
    """Apply a drag-and-drop of `items` onto `target`.

    Args:
        catalog: Supplies the formats and the extension of files created on folder drops.
        items: What was dragged.
        target: Where it was dropped.
        move: True to remove sources after copying (Ctrl not held).

    Returns:
        A status line summarising what happened.

    Raises:
        ValueError: For unsupported combinations or refused moves.
    """
    messages = [_drop_one(catalog, item, target, move) for item in items]
    return messages[-1] if len(messages) == 1 else f"{len(messages)} items {'moved' if move else 'copied'}"


def _drop_one(catalog: Catalog, item: LibraryItem, target: LibraryItem, move: bool) -> str:
    if item.kind == Kind.ENTRY and target.kind == Kind.FILE:
        return transfer_entry(catalog, item.path, item.index, target.path, move)
    if item.kind == Kind.ENTRY and target.is_directory:
        return entry_to_new_file(catalog, item.path, item.index, target.path)
    if item.kind == Kind.FILE and target.kind == Kind.FILE:
        return transfer_entry(catalog, item.path, 0, target.path, move=False)
    if item.kind == Kind.FILE and target.is_directory:
        return (move_files if move else copy_files)([item.path], target.path)
    raise ValueError(f"Can't drop a {item.kind.value} onto a {target.kind.value}")


def _safe_filename(name: str, fallback: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in " -_." else "_" for c in name).strip()
    return cleaned or fallback
