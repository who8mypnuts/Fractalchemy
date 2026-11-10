"""Crash recovery and the shelf of unsaved edits, for the main window's fractal.

`RecoveryKeeper` watches the `FractalDocument`:

* **While you edit**: a few seconds after the edits pause (`config.RECOVERY_DELAY_MS`) the unsaved fractal is written
  to this instance's recovery folder; saving (or undoing back to the saved state) removes it. A clean exit
  (`shutdown`) removes the folder. Each running instance holds a `QLockFile`, so an instance's folder without a live
  lock is what a crash left behind — `orphans()` — and the main window offers it at start-up (`ask_recovery`).
* **When another fractal is shown** while the current one has unsaved edits (`document.about_to_replace`), those edits
  are put on the *shelf* instead of being lost: switching fractals never asks, and *File ▸ Recover* lists the shelf.

Restoring goes through `FractalDocument.restore_unsaved`, so the fractal comes back modified and linked to the entry
it came from (*Save* writes it there). Everything lives under `config.RECOVERY_DIR` or the per-user cache folder; see
`fractalchemy/autosave.py` for the layout.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from PySide6.QtCore import QLockFile, QObject, QTimer, Signal
from PySide6.QtWidgets import QMessageBox, QWidget

from .. import config
from ..autosave import RecoveryEntry, RecoveryStore
from .fractal_document import FractalDocument

RESTORE, LATER, DISCARD = "restore", "later", "discard"


def recovery_folder() -> Path:
    """Where the recovery files live (`config.RECOVERY_DIR`, else the per-user cache folder's `recovery/`)."""
    if config.RECOVERY_DIR is not None:
        return Path(config.RECOVERY_DIR)
    from ..formulas.loader import cache_dir
    return cache_dir() / "recovery"


def ask_recovery(parent: QWidget, entry: RecoveryEntry, more: int) -> str:
    """The start-up question: *Restore* / *Not now* / *Discard* (returns `RESTORE`, `LATER` or `DISCARD`)."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle("Recover unsaved fractal")
    box.setText(f"Fractalchemy did not close properly last time. Restore the unsaved fractal {entry.describe}?")
    details = ", ".join(entry.labels[-5:])
    info = f"Its last edits: {details}." if details else ""
    if more:
        info += f" {more} more can be restored from File ▸ Recover."
    box.setInformativeText(info.strip() + " \"Not now\" keeps it under File ▸ Recover.")
    restore = box.addButton("Restore", QMessageBox.ButtonRole.AcceptRole)
    later = box.addButton("Not now", QMessageBox.ButtonRole.RejectRole)
    discard = box.addButton("Discard", QMessageBox.ButtonRole.DestructiveRole)
    box.setDefaultButton(restore)
    box.exec()
    clicked = box.clickedButton()
    return RESTORE if clicked is restore else DISCARD if clicked is discard else LATER if clicked is later else LATER


class RecoveryKeeper(QObject):
    """Keeps unsaved fractal edits recoverable (see the module docstring).

    Signals:
        changed(): The recoverable set changed (the shelf grew, an entry was restored or discarded).
    """
    changed = Signal()

    def __init__(self, document: FractalDocument, folder: Path | None = None, parent: QObject | None = None):
        super().__init__(parent)
        self.document = document
        self.store = RecoveryStore(folder or recovery_folder(), f"{os.getpid()}-{uuid.uuid4().hex[:8]}", config.SHELF_SIZE)
        self.store.lock_path().parent.mkdir(parents=True, exist_ok=True)
        self._lock = QLockFile(str(self.store.lock_path()))
        self._lock.setStaleLockTime(0)                   # never stale by age: only when its process is gone
        self._lock.tryLock(0)
        self._timer = QTimer(self, singleShot=True, interval=config.RECOVERY_DELAY_MS)
        self._timer.timeout.connect(self.write_now)
        document.edited.connect(self._on_edited)
        document.modified_changed.connect(self._on_modified_changed)
        document.about_to_replace.connect(self._shelve)

    # --- keeping the current fractal -----------------------------------------------------------------------------------
    def _labels(self) -> list[str]:
        position = self.document.history_position
        return [entry.label for entry in self.document.history()[1:position + 1]]

    def _on_edited(self, _kind: str) -> None:
        if self.document.modified:
            self._timer.start()

    def _on_modified_changed(self, modified: bool) -> None:
        if not modified:
            self._timer.stop()
            self.store.clear_current()

    @property
    def pending(self) -> bool:
        """True while a write is waiting for the edits to pause (tests)."""
        return self._timer.isActive()

    def write_now(self) -> None:
        """Write the unsaved fractal now (or remove the copy when nothing is unsaved)."""
        self._timer.stop()
        doc = self.document
        if doc.flame is not None and doc.modified:
            self.store.write_current(doc.flame, doc.source_path, doc.source_index, self._labels())
        else:
            self.store.clear_current()

    def _shelve(self) -> None:
        doc = self.document
        if doc.flame is not None and doc.modified:
            self._timer.stop()
            self.store.shelve(doc.flame, doc.source_path, doc.source_index, self._labels())
            self.store.clear_current()
            self.changed.emit()

    # --- what can be recovered ---------------------------------------------------------------------------------------------
    def is_alive(self, instance: str) -> bool:
        """Whether the instance that owns a session folder is still running (its lock is held)."""
        lock = QLockFile(str(self.store.lock_path(instance)))
        lock.setStaleLockTime(0)
        if lock.tryLock(0):
            lock.unlock()
            return False
        return True

    def orphans(self) -> list[RecoveryEntry]:
        """Unsaved fractals left by instances that crashed."""
        return self.store.orphans(self.is_alive)

    def shelf(self) -> list[RecoveryEntry]:
        return self.store.shelf()

    def restore(self, entry: RecoveryEntry) -> bool:
        """Show a recovered fractal (modified, linked to its source entry when that file still exists) and forget the
        recovery copy (it is this session's unsaved fractal now, kept like any other)."""
        try:
            flame = entry.load()
        except Exception:  # noqa: BLE001 - a damaged recovery file is reported by the caller and dropped
            self.discard(entry)
            return False
        source = Path(entry.source_path) if entry.source_path and Path(entry.source_path).is_file() else None
        self.store.discard(entry)
        self.document.restore_unsaved(flame, source, entry.source_index if source else 0, f"Recovered {entry.describe}")
        self.write_now()
        self.changed.emit()
        return True

    def discard(self, entry: RecoveryEntry) -> None:
        self.store.discard(entry)
        self.changed.emit()

    def clear_shelf(self) -> None:
        self.store.clear_shelf()
        self.changed.emit()

    def shutdown(self) -> None:
        """A clean exit: nothing of this session needs recovering."""
        self._timer.stop()
        self.store.close()
        self._lock.unlock()


def populate_recover_menu(menu, keeper: RecoveryKeeper, on_failed) -> None:
    """*File ▸ Recover*: what crashed sessions left, the shelf of unsaved edits, and *Clear shelf*."""
    menu.clear()
    orphans, shelf = keeper.orphans(), keeper.shelf()

    def restore(entry: RecoveryEntry) -> None:
        if not keeper.restore(entry):
            on_failed(entry)

    for entry in orphans:
        menu.addAction(f"From a crashed session: {entry.describe}", lambda _c=False, e=entry: restore(e))
    if orphans and shelf:
        menu.addSeparator()
    for entry in shelf:
        action = menu.addAction(f"Unsaved edits of {entry.describe}", lambda _c=False, e=entry: restore(e))
        action.setToolTip(", ".join(entry.labels[-5:]))
    if not orphans and not shelf:
        menu.addAction("Nothing to recover").setEnabled(False)
    menu.addSeparator()
    menu.addAction("Clear Shelf", keeper.clear_shelf).setEnabled(bool(shelf))


__all__ = ["RecoveryKeeper", "ask_recovery", "populate_recover_menu", "recovery_folder", "RESTORE", "LATER", "DISCARD"]
