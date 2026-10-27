"""What the gradient and fractal file actions share: background writes, failure reporting,
the unsaved-changes prompt, name prompts and "did we just write this file?" bookkeeping.

Subclasses implement the document-specific flows (open, save, save-as) on top of these.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QInputDialog, QMessageBox, QWidget

from .background import run_in_background

RECENT_WRITE_SECONDS = 3.0


class FileActionsBase(QObject):
    """Shared plumbing for document file actions.

    Signals:
        status(str): Outcome text for the status bar.
        file_written(Path): A file on disk changed because of us.
    """
    status = Signal(str)
    file_written = Signal(Path)

    def __init__(self, parent: QWidget):
        """Args:
            parent: Widget that owns dialogs and message boxes.
        """
        super().__init__(parent)
        self._parent = parent
        self._last_dir = str(Path.cwd())
        self._load_ticket = 0
        self._written: dict[Path, float] = {}

    # --- contract for subclasses ---------------------------------------------
    def save(self) -> bool:
        """Write the document to its own place (or ask where). Returns True if a write was started."""
        raise NotImplementedError

    def _document_name(self) -> str:
        """The name shown in prompts about the document."""
        raise NotImplementedError

    def _document_modified(self) -> bool:
        raise NotImplementedError

    # --- shared behaviour --------------------------------------------------------
    def confirm_discard(self) -> bool:
        """Ask about unsaved edits before replacing the document.

        Choosing Save starts the write (it completes in the background) and then
        proceeds; cancelling that save's dialog counts as Cancel here too.

        Returns:
            False if the caller should abort.
        """
        if not self._document_modified():
            return True
        buttons = QMessageBox.StandardButton
        answer = QMessageBox.question(
            self._parent, "Unsaved changes", f"'{self._document_name()}' has unsaved changes.",
            buttons.Save | buttons.Discard | buttons.Cancel, buttons.Save,
        )
        if answer == buttons.Save:
            return self.save()
        return answer == buttons.Discard

    def wrote_recently(self, path: Path) -> bool:
        """True if we wrote `path` within the last few seconds (to ignore our own watcher events)."""
        return time.monotonic() - self._written.get(path, -1e9) < RECENT_WRITE_SECONDS

    def _next_load_ticket(self) -> int:
        """A new ticket; a load whose ticket is stale by the time it finishes must not replace the document."""
        self._load_ticket += 1
        return self._load_ticket

    def _is_current_ticket(self, ticket: int) -> bool:
        return ticket == self._load_ticket

    def _run_write(self, path: Path, fn: Callable, *args, on_done: Callable, failure_title: str = "Could not save file") -> None:
        """Run a writer on the thread pool; on success note the write, remember the folder and announce the file."""
        def done(result) -> None:
            self._written[path] = time.monotonic()
            self._remember(path)
            on_done(result)
            self.file_written.emit(path)

        # recorded *before* the write too: the file watcher's event can reach the GUI thread before `done` runs
        self._written[path] = time.monotonic()
        run_in_background(fn, *args, on_done=done, on_error=lambda exc: self._fail(failure_title, exc))

    def _ask_name(self, what: str, default: str) -> str | None:
        """Prompt for an entry name; None if cancelled or blank."""
        name, ok = QInputDialog.getText(self._parent, f"{what.capitalize()} name", f"Save {what} as:", text=default)
        return name.strip() if ok and name.strip() else None

    def _remember(self, path: Path) -> None:
        self._last_dir = str(path.parent)

    def _fail(self, title: str, exc: Exception, quiet: bool = False) -> None:
        """Report a failure on the status bar and, unless `quiet`, in a warning box."""
        self.status.emit(f"{title}: {exc}")
        if not quiet:
            QMessageBox.warning(self._parent, title, str(exc))
