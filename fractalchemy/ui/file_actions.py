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
from ..formats import DEFAULT_SAVE_FORMAT, append_dialog_filter, format_for, open_dialog_filter, save_dialog_filter, save_gradient
from ..model import Gradient
from .background import run_in_background
from .document import GradientDocument
from .file_workers import append_entry, load_entries, write_file

RECENT_WRITE_SECONDS = 3.0


class FileActions(QObject):
    """Open / Save / Save As flows for the document; all disk work runs on the thread pool.

    Signals:
        status(str): Outcome text for the status bar.
        file_written(Path): A file on disk changed because of us.
        entries_loaded(Path | None, list[Gradient]): All gradients of the newly opened file.
        entry_saved(int, Gradient): One entry was written in place.
    """
    status = Signal(str)
    file_written = Signal(Path)
    entries_loaded = Signal(object, list)
    entry_saved = Signal(int, object)

    def __init__(self, document: GradientDocument, parent: QWidget):
        """Args:
            document: The document to load into and save from.
            parent: Widget that owns dialogs and message boxes.
        """
        super().__init__(parent)
        self._document = document
        self._parent = parent
        self._last_dir = str(Path.cwd())
        self._load_ticket = 0
        self._entries: list[Gradient] = []
        self._written: dict[Path, float] = {}

    # --- opening ------------------------------------------------------------
    def open(self) -> None:
        """Prompt for a file and open its first gradient (after checking for unsaved edits)."""
        if not self.confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(self._parent, "Open gradient source", self._last_dir, open_dialog_filter())
        if path:
            self.open_path(Path(path))

    def open_path(self, path: Path, index: int = 0, note: str | None = None) -> None:
        """Load every gradient in `path` on a worker thread, then show entry `index`.
        `note` replaces the usual 'Loaded…' status message."""
        self._load_ticket += 1
        ticket = self._load_ticket
        self.status.emit(f"Loading {path.name}…")
        run_in_background(
            load_entries, path,
            on_done=lambda gradients: self._loaded(gradients, path, index, ticket, note),
            on_error=lambda exc: self._fail("Could not open file", exc),
        )

    def show_gradient(self, gradient: Gradient) -> None:
        """Show a gradient that did not come from a file (the strip lists just it)."""
        self._load_ticket += 1   # a load still in flight must not replace this
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
        name = self._ask_name()
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
        name = self._ask_name() if path else None
        if not name:
            return False
        self._append_to(Path(path), name)
        return True

    def confirm_discard(self) -> bool:
        """Ask about unsaved edits before replacing the document.

        Choosing Save starts the write (it completes in the background) and then
        proceeds; cancelling that save's dialog counts as Cancel here too.

        Returns:
            False if the caller should abort.
        """
        if not self._document.modified:
            return True
        buttons = QMessageBox.StandardButton
        answer = QMessageBox.question(
            self._parent, "Unsaved changes", f"'{self._document.gradient.name}' has unsaved changes.",
            buttons.Save | buttons.Discard | buttons.Cancel, buttons.Save,
        )
        if answer == buttons.Save:
            return self.save()
        return answer == buttons.Discard

    def wrote_recently(self, path: Path) -> bool:
        """True if we wrote `path` within the last few seconds (to ignore our own watcher events)."""
        return time.monotonic() - self._written.get(path, -1e9) < RECENT_WRITE_SECONDS

    # --- helpers ------------------------------------------------------------
    def _loaded(self, gradients: list[Gradient], path: Path, index: int, ticket: int, note: str | None = None) -> None:
        if ticket != self._load_ticket:
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

    def _run_write(self, path: Path, fn, *args, on_done) -> None:
        """Run a writer on the thread pool; on success note the write and announce the file."""
        def done(result) -> None:
            self._written[path] = time.monotonic()
            self._remember(path)
            on_done(result)
            self.file_written.emit(path)

        # recorded *before* the write too: the file watcher's event can reach the GUI thread before `done` runs
        self._written[path] = time.monotonic()
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
