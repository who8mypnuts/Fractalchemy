"""Open / Save / Save As, driving a GradientDocument. All disk work is backgrounded.

The file's full list of gradients ("entries") is kept here so the browser strip
and the editor stay in step: the document always edits a *copy* of an entry,
and the entry is replaced only when a save succeeds.
"""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QWidget

from .. import config
from ..formats import (
    DEFAULT_SAVE_FORMAT, append_dialog_filter, format_for, load_gradients, open_dialog_filter, save_dialog_filter,
    save_gradient,
)
from ..model import Gradient
from .background import run_in_background
from .document import GradientDocument

RECENT_WRITE_SECONDS = 3.0


class FileActions(QObject):
    status = Signal(str)                 # short human-readable outcome, e.g. for the status bar
    file_written = Signal(Path)          # a file on disk changed because of us
    entries_loaded = Signal(object, list)  # Path | None, list[Gradient] — all gradients of the open file
    entry_saved = Signal(int, object)    # index, Gradient — one entry was written in place

    def __init__(self, document: GradientDocument, parent: QWidget):
        super().__init__(parent)
        self._document = document
        self._parent = parent
        self._last_dir = str(Path.cwd())
        self._load_ticket = 0
        self._entries: list[Gradient] = []
        self._written: dict[Path, float] = {}

    # --- opening ------------------------------------------------------------
    def open(self) -> None:
        if not self.confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(self._parent, "Open gradient source", self._last_dir, open_dialog_filter())
        if path:
            self.open_path(Path(path))

    def open_path(self, path: Path, index: int = 0) -> None:
        """Load every gradient in `path` on a worker thread, then show entry `index`."""
        self._load_ticket += 1
        ticket = self._load_ticket
        self.status.emit(f"Loading {path.name}…")
        run_in_background(
            load_gradients, path,
            on_done=lambda gradients: self._loaded(gradients, path, index, ticket),
            on_error=lambda exc: self._fail("Could not open file", exc),
        )

    def show_entry(self, index: int) -> None:
        """Switch the editor to another already-loaded entry of the current file."""
        path = self._document.source_path
        if not 0 <= index < len(self._entries) or path is None:
            return
        if self._document.is_showing(path, index) and not self._document.modified:
            return
        if self.confirm_discard():
            self._document.replace(self._entries[index].copy(), path, index)

    # --- saving -------------------------------------------------------------
    def save(self) -> None:
        target = self._writable_source_path()
        if target is None:
            return self.save_as_new_file()
        gradient = self._document.gradient
        index = self._document.source_index
        self._run_write(save_gradient, gradient, target, index, on_done=lambda _: self._saved_in_place(gradient, target, index))

    def save_as_new_entry(self) -> None:
        """Append the edited gradient to its own file under a (possibly new) name."""
        path = self._document.source_path
        if path is None or not format_for(path).can_append:
            return self.save_as_into_file()
        name = self._ask_name()
        if name:
            self._append_to(path, name)

    def save_as_new_file(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self._parent, "Save gradient as new file", str(self._suggested_save_path()), save_dialog_filter())
        if path:
            gradient = self._document.gradient.copy()
            self._run_write(_create_file, gradient, Path(path), on_done=lambda _: self.open_path(Path(path), 0))

    def save_as_into_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self._parent, "Add gradient to an existing file", self._last_dir, append_dialog_filter())
        if path:
            name = self._ask_name()
            if name:
                self._append_to(Path(path), name)

    def confirm_discard(self) -> bool:
        """Ask about unsaved edits. Returns False if the caller should abort."""
        if not self._document.modified:
            return True
        buttons = QMessageBox.StandardButton
        answer = QMessageBox.question(
            self._parent, "Unsaved changes", f"'{self._document.gradient.name}' has unsaved changes.",
            buttons.Save | buttons.Discard | buttons.Cancel, buttons.Save,
        )
        if answer == buttons.Save:
            self.save()
        return answer != buttons.Cancel

    def wrote_recently(self, path: Path) -> bool:
        return time.monotonic() - self._written.get(path, -1e9) < RECENT_WRITE_SECONDS

    # --- helpers ------------------------------------------------------------
    def _loaded(self, gradients: list[Gradient], path: Path, index: int, ticket: int) -> None:
        if ticket != self._load_ticket:
            return  # a newer load superseded this one
        index = min(index, len(gradients) - 1)
        self._remember(path)
        self._entries = gradients
        self.entries_loaded.emit(path, gradients)
        self._document.replace(gradients[index].copy(), path, index)
        self.status.emit(f"Loaded '{gradients[index].name}' from {path.name} ({len(gradients[index])} nodes)")

    def _append_to(self, path: Path, name: str) -> None:
        gradient = self._document.gradient.copy()
        gradient.name = name
        self._run_write(_append_entry, gradient, path, on_done=lambda new_index: self.open_path(path, new_index))

    def _run_write(self, fn, *args, on_done) -> None:
        def done(result) -> None:
            path = next(a for a in args if isinstance(a, Path))
            self._written[path] = time.monotonic()
            self._remember(path)
            on_done(result)
            self.file_written.emit(path)

        run_in_background(fn, *args, on_done=done, on_error=lambda exc: self._fail("Could not save file", exc))

    def _saved_in_place(self, gradient: Gradient, path: Path, index: int) -> None:
        if self._document.gradient is gradient:  # user may have moved on meanwhile
            self._document.mark_saved(path, index)
        if index < len(self._entries):
            self._entries[index] = gradient.copy()
        self.entry_saved.emit(index, gradient)
        self.status.emit(f"Saved '{gradient.name}' to {path.name}")

    def _ask_name(self) -> str | None:
        name, ok = QInputDialog.getText(self._parent, "Gradient name", "Save gradient as:", text=self._document.gradient.name)
        return name.strip() if ok and name.strip() else None

    def _writable_source_path(self) -> Path | None:
        fmt = self._document.source_format
        return self._document.source_path if fmt is not None and fmt.can_save else None

    def _suggested_save_path(self) -> Path:
        source = self._document.source_path
        ext = DEFAULT_SAVE_FORMAT.extensions[0]
        stem = self._document.gradient.name or (source.stem if source else config.APP_NAME.lower())
        return Path(self._last_dir) / f"{stem}{ext}"

    def _remember(self, path: Path) -> None:
        self._last_dir = str(path.parent)

    def _fail(self, title: str, exc: Exception) -> None:
        QMessageBox.warning(self._parent, title, str(exc))
        self.status.emit(f"{title}: {exc}")


# --- worker functions (no Qt) ------------------------------------------------
def _append_entry(gradient: Gradient, path: Path) -> int:
    fmt = format_for(path)
    if not (fmt.can_append if path.exists() else fmt.can_create):
        raise ValueError(f"Gradients cannot be added to {fmt.name} files")
    fmt.append(gradient, path)
    return len(fmt.names(path)) - 1


def _create_file(gradient: Gradient, path: Path) -> None:
    fmt = format_for(path)
    if not fmt.can_create:
        raise ValueError(f"New {fmt.name} files cannot be created; choose another format")
    if path.exists():
        path.unlink()  # the save dialog already confirmed the overwrite
    if fmt.can_append:
        fmt.append(gradient, path)
    else:
        fmt.save(gradient, path)
