"""Save / Save As flows for the fractal shown in the main window. Nothing is written unless asked.

    Save                  — overwrite the entry the flame came from (.flame / .fa); else "as new file"
    Save As ▸ New Entry   — append to the same file under a (possibly new) name
    Save As ▸ New File…   — a new .flame / .fa file (an existing file is appended to, never wiped)
    Save As ▸ Into File…  — append to a chosen existing file

Disk work runs on the thread pool; the document's source moves to the written entry on success, so
further Saves go there. `wrote_recently()` lets the library's file watcher ignore our own writes.
"""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QWidget

from .. import config
from ..fractal.formats import DEFAULT_SAVE_FORMAT, fractal_format_for, save_dialog_filter
from ..fractal.scene import Flame
from .background import run_in_background
from .fractal_document import FractalDocument

RECENT_WRITE_SECONDS = 3.0


def _write_replace(flame: Flame, path: Path, index: int) -> int:
    fractal_format_for(path).replace(flame, path, index)
    return index


def _write_append(flame: Flame, path: Path) -> int:
    return fractal_format_for(path).append(flame, path)


class FractalFileActions(QObject):
    """Save flows for a `FractalDocument`.

    Signals:
        status(str): Outcome text for the status bar.
        file_written(Path, int): A file entry was written by us (path, index).
    """
    status = Signal(str)
    file_written = Signal(object, int)

    def __init__(self, document: FractalDocument, parent: QWidget):
        super().__init__(parent)
        self._document = document
        self._parent = parent
        self._last_dir = str(Path.cwd())
        self._written: dict[Path, float] = {}

    # --- facts -------------------------------------------------------------------------------------------
    def can_save_in_place(self) -> bool:
        """True when the flame came from an entry we can overwrite."""
        path = self._document.source_path
        return path is not None and self._document.flame is not None and fractal_format_for(path).can_replace

    def can_append_to_source(self) -> bool:
        path = self._document.source_path
        return path is not None and self._document.flame is not None and fractal_format_for(path).can_append

    def wrote_recently(self, path: Path) -> bool:
        return time.monotonic() - self._written.get(path, -1e9) < RECENT_WRITE_SECONDS

    # --- flows -------------------------------------------------------------------------------------------
    def save(self) -> bool:
        """Overwrite the source entry; falls back to Save As ▸ New File for read-only / unsaved flames.

        Returns:
            True if a write was started.
        """
        if self._document.flame is None:
            return False
        if not self.can_save_in_place():
            return self.save_as_new_file()
        path, index = self._document.source_path, self._document.source_index
        self._run(path, _write_replace, self._document.flame.copy(), path, index, verb="Saved")
        return True

    def save_as_new_entry(self) -> bool:
        """Append the flame to its own file under a name of the user's choosing."""
        if self._document.flame is None:
            return False
        if not self.can_append_to_source():
            return self.save_as_into_file()
        name = self._ask_name()
        if not name:
            return False
        flame = self._document.flame.copy()
        flame.name = name
        self._run(self._document.source_path, _write_append, flame, self._document.source_path, verb="Added")
        return True

    def save_as_new_file(self) -> bool:
        """Prompt for a path and write the flame there (an existing multi-flame file is appended to)."""
        if self._document.flame is None:
            return False
        path, _ = QFileDialog.getSaveFileName(self._parent, "Save fractal as new file", str(self._suggested_path()),
                                              save_dialog_filter(), options=QFileDialog.Option.DontConfirmOverwrite)
        if not path:
            return False
        target = Path(path)
        if not target.suffix:
            target = target.with_suffix(DEFAULT_SAVE_FORMAT.extensions[0])
        try:
            fractal_format_for(target)
        except ValueError as exc:
            self._fail("Cannot save fractal", exc)
            return False
        self._last_dir = str(target.parent)
        self._run(target, _write_append, self._document.flame.copy(), target, verb="Saved")
        return True

    def save_as_into_file(self) -> bool:
        """Append the flame to a chosen existing file under a name of the user's choosing."""
        if self._document.flame is None:
            return False
        path, _ = QFileDialog.getOpenFileName(self._parent, "Add fractal to an existing file", self._last_dir, save_dialog_filter())
        name = self._ask_name() if path else None
        if not name:
            return False
        flame = self._document.flame.copy()
        flame.name = name
        self._last_dir = str(Path(path).parent)
        self._run(Path(path), _write_append, flame, Path(path), verb="Added")
        return True

    # --- helpers -----------------------------------------------------------------------------------------
    def _run(self, path: Path, fn, *args, verb: str) -> None:
        self._written[path] = time.monotonic()
        flame = args[0]

        def done(index: int) -> None:
            self._written[path] = time.monotonic()
            if self._document.flame is not None:
                self._document.flame.name = flame.name
            self._document.set_source(path, index)
            self._document.mark_saved()
            self.file_written.emit(path, index)
            self.status.emit(f"{verb} '{flame.name}' in {path.name}")

        run_in_background(fn, *args, on_done=done, on_error=lambda exc: self._fail("Could not save fractal", exc))

    def _ask_name(self) -> str | None:
        current = self._document.flame.name if self._document.flame else ""
        name, ok = QInputDialog.getText(self._parent, "Fractal name", "Save fractal as:", text=current)
        return name.strip() if ok and name.strip() else None

    def _suggested_path(self) -> Path:
        source = self._document.source_path
        flame = self._document.flame
        stem = (flame.name if flame else "") or (source.stem if source else config.APP_NAME.lower())
        folder = source.parent if source else Path(self._last_dir)
        ext = source.suffix if source and fractal_format_for(source).can_append else DEFAULT_SAVE_FORMAT.extensions[0]
        return folder / f"{stem}{ext}"

    def _fail(self, title: str, exc: Exception) -> None:
        QMessageBox.warning(self._parent, title, str(exc))
        self.status.emit(f"{title}: {exc}")
