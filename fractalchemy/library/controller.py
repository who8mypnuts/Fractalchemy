"""Coordinates roots, background scans, and file operations for the library.

Everything that touches the disk goes through `run_in_background`; the model is
rebuilt from the results on the GUI thread. Dialogs live elsewhere: this class
only emits `status` / `failed` strings.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QGuiApplication

from ..ui.background import run_in_background
from . import operations as ops
from .items import Kind, LibraryItem
from .model import LibraryModel
from .payload import from_mime, to_mime
from .roots import LibraryRoots
from .scanner import ScannedDir, scan_directory
from .watcher import LibraryWatcher


class LibraryController(QObject):
    """Owns the roots, scans them in the background, and runs file operations.

    Signals:
        status(str): Something succeeded; show it.
        failed(str): Something failed; show it.
        root_scanned(Path): A root's subtree was rebuilt.
        scanning(bool): Whether any scan is in flight.
        file_changed_externally(Path): Another program changed a watched file.
    """
    status = Signal(str)
    failed = Signal(str)
    root_scanned = Signal(Path)
    scanning = Signal(bool)
    file_changed_externally = Signal(Path)

    def __init__(self, model: LibraryModel, roots: LibraryRoots, parent: QObject | None = None):
        """Args:
            model: The tree model to populate.
            roots: The persisted folder list.
            parent: Qt parent.
        """
        super().__init__(parent)
        self.model = model
        self.catalog = model.catalog
        self.roots = roots
        self._generation: dict[Path, int] = defaultdict(int)
        self._pending = 0
        self._opened: Path | None = None
        self.watcher = LibraryWatcher(self)
        roots.added.connect(self.rescan_root)
        roots.removed.connect(self._on_root_removed)
        model.drop_requested.connect(self.drop)
        self.watcher.root_changed.connect(self.rescan_root)
        self.watcher.file_changed.connect(self.file_changed_externally)
        self.watcher.file_changed.connect(self._on_file_changed)

    # --- the opened file --------------------------------------------------------
    @property
    def opened_file(self) -> Path | None:
        """File shown in the temporary section above the roots, or None."""
        return self._opened

    def set_opened_file(self, path: Path | None) -> None:
        """Show `path`'s entries above the roots (replacing any previous opened file); None clears."""
        self._opened = Path(path).resolve() if path is not None else None
        self.watcher.watch_file(self._opened)
        if self._opened is None:
            self.model.clear_opened_file()
            return
        self.refresh_opened_file()

    def refresh_opened_file(self) -> None:
        """Re-list the opened file's entries (after it changed)."""
        path = self._opened
        if path is None:
            return
        run_in_background(self.catalog.entry_names, path,
                          on_done=lambda names: self._apply_opened(path, names),
                          on_error=lambda exc: self._opened_unreadable(path, exc))

    def _apply_opened(self, path: Path, names: list[str]) -> None:
        if path != self._opened:
            return
        if names:
            self.model.set_opened_file(path, names)
        else:
            self.model.clear_opened_file()
            self.status.emit(f"{path.name} holds no {self.catalog.entry_label}s")

    def _opened_unreadable(self, path: Path, exc: Exception) -> None:
        """A refresh failed — often a file caught mid-write by the watcher: keep the section as it is, just say so."""
        if path == self._opened:
            self.status.emit(f"Could not re-read {path.name}: {exc}")

    def _on_file_changed(self, path: Path) -> None:
        if self._opened is not None and Path(path).resolve() == self._opened:
            self.refresh_opened_file()

    # --- scanning -----------------------------------------------------------
    def rescan_all(self) -> None:
        """Rescan every root."""
        for path in self.roots.paths():
            self.rescan_root(path)

    def rescan_root(self, path: Path) -> None:
        """Rescan one root; stale results from earlier scans are discarded."""
        self._generation[path] += 1
        generation = self._generation[path]
        self._set_pending(+1)
        run_in_background(
            scan_directory, path, self.catalog,
            on_done=lambda scanned: self._apply_scan(scanned, generation),
            on_error=lambda exc: self._scan_failed(path, exc),
        )

    def rescan_containing(self, *paths: Path) -> None:
        """Rescan each root that contains any of `paths`."""
        for root in {r for r in self.roots.paths() for p in paths if _is_within(p, r)}:
            self.rescan_root(root)

    def root_of(self, path: Path) -> Path | None:
        """The library root containing `path`, or None."""
        return next((r for r in self.roots.paths() if _is_within(path, r)), None)

    # --- operations (all run off the GUI thread) ---------------------------
    def drop(self, items: list[LibraryItem], target: LibraryItem, move: bool) -> None:
        """Perform a drag-and-drop (or paste) of `items` onto `target`."""
        affected = [i.path for i in items] + [target.path]
        self._run(ops.drop_items, self.catalog, items, target, move, affected=affected)

    def duplicate(self, item: LibraryItem) -> None:
        """Copy a file alongside itself, or an entry within its file."""
        if item.kind == Kind.ENTRY:
            self._run(ops.duplicate_entry, self.catalog, item.path, item.index, affected=[item.path])
        elif item.kind == Kind.FILE:
            self._run(ops.duplicate_file, item.path, affected=[item.path])

    def delete(self, items: list[LibraryItem]) -> None:
        """Delete files / folders (to the trash when possible) or entries."""
        for item in items:
            if item.kind == Kind.ENTRY:
                self._run(ops.delete_entry, self.catalog, item.path, item.index, affected=[item.path])
            elif item.kind in (Kind.FILE, Kind.DIR):
                self._run(ops.delete_path, item.path, affected=[item.path])

    def rename(self, item: LibraryItem, new_name: str) -> None:
        """Rename a file, folder or entry."""
        if item.kind == Kind.ENTRY:
            self._run(ops.rename_entry, self.catalog, item.path, item.index, new_name, affected=[item.path])
        elif item.kind in (Kind.FILE, Kind.DIR):
            self._run(ops.rename_path, item.path, new_name, affected=[item.path])

    def new_folder(self, target: LibraryItem, name: str) -> None:
        """Create a sub-folder in the folder of `target`."""
        self._run(ops.create_folder, target.directory, name, affected=[target.directory])

    def copy_to_clipboard(self, items: list[LibraryItem]) -> None:
        """Put `items` on the clipboard for a later `paste`."""
        QGuiApplication.clipboard().setMimeData(to_mime(items, self.catalog.key))
        self.status.emit(f"Copied {len(items)} item(s)")

    def paste(self, target: LibraryItem) -> None:
        """Drop whatever is on the clipboard onto `target` as a copy."""
        items = from_mime(QGuiApplication.clipboard().mimeData(), self.catalog.key)
        if items and self.model.canDropMimeData(QGuiApplication.clipboard().mimeData(), None, 0, 0, self.model.index_for(target)):
            self.drop(items, target, move=False)
        else:
            self.failed.emit("Nothing on the clipboard can be pasted here")

    def reveal(self, item: LibraryItem) -> None:
        """Open the item's folder in the system file manager."""
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(item.directory)))

    def remove_root(self, path: Path) -> None:
        """Remove a folder from the library (files on disk are untouched)."""
        self.roots.remove(path)
        self.status.emit(f"Removed {path.name} from the library")

    # --- internals ----------------------------------------------------------
    def _run(self, fn: Callable, *args, affected: list[Path]) -> None:
        def done(message: str) -> None:
            self.status.emit(message)
            self._refresh(affected)

        def error(exc: Exception) -> None:
            self.failed.emit(str(exc))
            self._refresh(affected)

        run_in_background(fn, *args, on_done=done, on_error=error)

    def _refresh(self, affected: list[Path]) -> None:
        self.rescan_containing(*affected)
        if self._opened is not None and any(Path(p).resolve() == self._opened for p in affected):
            self.refresh_opened_file()

    def _apply_scan(self, scanned: ScannedDir, generation: int) -> None:
        self._set_pending(-1)
        if generation != self._generation[scanned.path] or scanned.path not in self.roots.paths():
            return  # superseded or removed meanwhile
        self.model.set_root(scanned)
        self.watcher.track(scanned)
        self.root_scanned.emit(scanned.path)

    def _scan_failed(self, path: Path, exc: Exception) -> None:
        self._set_pending(-1)
        self.failed.emit(f"Could not scan {path}: {exc}")

    def _on_root_removed(self, path: Path) -> None:
        self._generation[path] += 1
        self.model.remove_root(path)
        self.watcher.forget(path)

    def _set_pending(self, delta: int) -> None:
        was_busy = self._pending > 0
        self._pending = max(0, self._pending + delta)
        if was_busy != (self._pending > 0):
            self.scanning.emit(self._pending > 0)


def _is_within(path: Path, root: Path) -> bool:
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False
