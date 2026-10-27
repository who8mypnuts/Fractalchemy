"""Open / Save / Save As, driving a GradientDocument. All disk work is backgrounded.

The file's full list of gradients ("entries") is kept here so the browser strip
and the editor stay in step: the document always edits a *copy* of an entry,
and the entry is replaced only when a save succeeds.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFileDialog, QWidget

from .. import config
from ..formats import DEFAULT_SAVE_FORMAT, append_dialog_filter, format_for, open_dialog_filter, save_dialog_filter, save_gradient
from ..model import Gradient
from .background import run_in_background
from .document import GradientDocument
from .file_actions_base import FileActionsBase
from .file_workers import append_entry, load_entries, write_file


class FileActions(FileActionsBase):
    """Open / Save / Save As flows for the gradient document; all disk work runs on the thread pool.

    Signals (besides the base class's `status` / `file_written`):
        entries_loaded(Path | None, list[Gradient]): All gradients of the newly opened file.
        entry_saved(int, Gradient): One entry was written in place.
    """
    entries_loaded = Signal(object, list)
    entry_saved = Signal(int, object)

    def __init__(self, document: GradientDocument, parent: QWidget):
        """Args:
            document: The document to load into and save from.
            parent: Widget that owns dialogs and message boxes.
        """
        super().__init__(parent)
        self._document = document
        self._entries: list[Gradient] = []

    def _document_name(self) -> str:
        return self._document.gradient.name

    def _document_modified(self) -> bool:
        return self._document.modified

    # --- opening ------------------------------------------------------------
    def open(self) -> None:
        """Prompt for a file and open its first gradient (after checking for unsaved edits)."""
        if not self.confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(self._parent, "Open gradient source", self._last_dir, open_dialog_filter())
        if path:
            self.open_path(Path(path))

    def open_path(self, path: Path, index: int = 0, note: str | None = None, quiet: bool = False) -> None:
        """Load every gradient in `path` on a worker thread, then show entry `index`.

        Args:
            path: The file.
            index: Entry to show.
            note: Replaces the usual "Loaded…" status message.
            quiet: Report failure on the status bar only (for reloads triggered by the file watcher).
        """
        ticket = self._next_load_ticket()
        self.status.emit(f"Loading {path.name}…")
        run_in_background(
            load_entries, path,
            on_done=lambda gradients: self._loaded(gradients, path, index, ticket, note),
            on_error=lambda exc: self._fail("Could not open file", exc, quiet),
        )

    def show_gradient(self, gradient: Gradient) -> None:
        """Show a gradient that did not come from a file (the strip lists just it)."""
        self._next_load_ticket()   # a load still in flight must not replace this
        self._entries = [gradient.copy()]
        self.entries_loaded.emit(None, self._entries)
        self._document.replace(gradient.copy())

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
    def save(self) -> bool:
        """Write the gradient back into its own slot; falls back to 'new file' for read-only sources.

        Returns:
            True if a write was started (False if a needed dialog was cancelled).
        """
        target = self._writable_source_path()
        if target is None:
            return self.save_as_new_file()
        gradient = self._document.gradient
        index = self._document.source_index
        self._run_write(target, save_gradient, gradient, target, index,
                        on_done=lambda _: self._saved_in_place(gradient, target, index))
        return True

    def save_as_new_entry(self) -> bool:
        """Append the edited gradient to its own file under a (possibly new) name.

        Returns:
            True if a write was started.
        """
        path = self._document.source_path
        if path is None or not format_for(path).can_append:
            return self.save_as_into_file()
        name = self._ask_name("gradient", self._document.gradient.name)
        if not name:
            return False
        self._append_to(path, name)
        return True

    def save_as_new_file(self) -> bool:
        """Prompt for a path and write the gradient there (existing multi-gradient files are appended to, never wiped).

        Returns:
            True if a write was started.
        """
        path, _ = QFileDialog.getSaveFileName(self._parent, "Save gradient as new file", str(self._suggested_save_path()), save_dialog_filter())
        if not path:
            return False
        gradient = self._document.gradient.copy()
        self._run_write(Path(path), write_file, gradient, Path(path), self._source(),
                        on_done=lambda result: self._wrote_file(Path(path), *result))
        return True

    def _wrote_file(self, path: Path, index: int, note: str) -> None:
        self.open_path(path, index, note or None)

    def save_as_into_file(self) -> bool:
        """Prompt for an existing file and append the gradient to it under a chosen name.

        Returns:
            True if a write was started.
        """
        path, _ = QFileDialog.getOpenFileName(self._parent, "Add gradient to an existing file", self._last_dir, append_dialog_filter())
        name = self._ask_name("gradient", self._document.gradient.name) if path else None
        if not name:
            return False
        self._append_to(Path(path), name)
        return True

    # --- helpers ------------------------------------------------------------
    def _loaded(self, gradients: list[Gradient], path: Path, index: int, ticket: int, note: str | None = None) -> None:
        if not self._is_current_ticket(ticket):
            return  # a newer load superseded this one
        index = min(index, len(gradients) - 1)
        self._remember(path)
        self._entries = gradients
        self.entries_loaded.emit(path, gradients)
        self._document.replace(gradients[index].copy(), path, index)
        self.status.emit(note or f"Loaded '{gradients[index].name}' from {path.name} ({len(gradients[index])} nodes)")

    def _append_to(self, path: Path, name: str) -> None:
        gradient = self._document.gradient.copy()
        gradient.name = name
        self._run_write(path, append_entry, gradient, path, self._source(),
                        on_done=lambda new_index: self.open_path(path, new_index))

    def _source(self) -> tuple[Path, int] | None:
        """Where the edited gradient came from — lets flame saves clone the fractal around the palette."""
        path = self._document.source_path
        return (path, self._document.source_index) if path is not None else None

    def _saved_in_place(self, gradient: Gradient, path: Path, index: int) -> None:
        if self._document.gradient is gradient:  # user may have moved on meanwhile
            self._document.mark_saved(path, index)
        if index < len(self._entries):
            self._entries[index] = gradient.copy()
        self.entry_saved.emit(index, gradient)
        self.status.emit(f"Saved '{gradient.name}' to {path.name}")

    def _writable_source_path(self) -> Path | None:
        fmt = self._document.source_format
        return self._document.source_path if fmt is not None and fmt.can_save else None

    def _suggested_save_path(self) -> Path:
        source = self._document.source_path
        ext = DEFAULT_SAVE_FORMAT.extensions[0]
        stem = self._document.gradient.name or (source.stem if source else config.APP_NAME.lower())
        return Path(self._last_dir) / f"{stem}{ext}"

