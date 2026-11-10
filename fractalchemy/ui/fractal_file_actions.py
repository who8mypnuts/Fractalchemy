"""Save / Save As flows for the fractal shown in the main window. Nothing is written unless asked.

    Save                  — overwrite the entry the flame came from (.flame / .fa); else "as new file"
    Save As ▸ New Entry   — append to the same file under a (possibly new) name
    Save As ▸ New File…   — a new .flame / .fa / .chaos file (an existing file is appended to, never wiped)
    Save As ▸ Into File…  — append to a chosen existing file

Disk work runs on the thread pool (`FileActionsBase._run_write`); the document's source moves to the written entry on
success, so further Saves go there, and the flame takes the name it was saved under through `FractalDocument.rename`
(the file actions never touch the document's flame themselves). `wrote_recently()` lets the library's file watcher
ignore our own writes. `confirm_discard()` (from the base) is what quitting asks with unsaved fractal edits.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from .. import config
from ..fractal.formats import DEFAULT_SAVE_FORMAT, fractal_format_for, save_dialog_filter
from ..fractal.scene import Flame
from .file_actions_base import FileActionsBase
from .fractal_document import FractalDocument

FAILURE_TITLE = "Could not save fractal"


def _write_replace(flame: Flame, path: Path, index: int) -> int:
    fractal_format_for(path).replace(flame, path, index)
    return index


def _write_append(flame: Flame, path: Path) -> int:
    return fractal_format_for(path).append(flame, path)


class FractalFileActions(FileActionsBase):
    """Save flows for a `FractalDocument`.

    Signals (besides the base's `status` and `file_written(Path)`):
        entry_written(Path, int): A file entry was written by us (path, index).
    """
    entry_written = Signal(object, int)

    def __init__(self, document: FractalDocument, parent: QWidget):
        super().__init__(parent)
        self._document = document

    # --- FileActionsBase contract ----------------------------------------------------------------------------------
    def _document_name(self) -> str:
        return self._document.flame.name if self._document.flame is not None else "the fractal"

    def _document_modified(self) -> bool:
        return self._document.modified

    # --- facts -------------------------------------------------------------------------------------------
    def can_save_in_place(self) -> bool:
        """True when the flame came from an entry we can overwrite."""
        path = self._document.source_path
        return path is not None and self._document.flame is not None and fractal_format_for(path).can_replace

    def can_append_to_source(self) -> bool:
        path = self._document.source_path
        return path is not None and self._document.flame is not None and fractal_format_for(path).can_append

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
        return self._write(path, _write_replace, self._document.flame.copy(), path, index, verb="Saved")

    def save_as_new_entry(self) -> bool:
        """Append the flame to its own file under a name of the user's choosing."""
        if self._document.flame is None:
            return False
        if not self.can_append_to_source():
            return self.save_as_into_file()
        name = self._ask_name("fractal", self._document.flame.name)
        if not name:
            return False
        flame = self._document.flame.copy()
        flame.name = name
        return self._write(self._document.source_path, _write_append, flame, self._document.source_path, verb="Added")

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
        self._remember(target)
        return self._write(target, _write_append, self._document.flame.copy(), target, verb="Saved")

    def save_as_into_file(self) -> bool:
        """Append the flame to a chosen existing file under a name of the user's choosing."""
        if self._document.flame is None:
            return False
        path, _ = QFileDialog.getOpenFileName(self._parent, "Add fractal to an existing file", self._last_dir, save_dialog_filter())
        name = self._ask_name("fractal", self._document.flame.name) if path else None
        if not name:
            return False
        flame = self._document.flame.copy()
        flame.name = name
        self._remember(Path(path))
        return self._write(Path(path), _write_append, flame, Path(path), verb="Added")

    # --- helpers -----------------------------------------------------------------------------------------
    def _confirm_lossy_save(self, flame: Flame) -> bool:
        """A flame using variations no loaded formula provides loses them when written: ask first."""
        if not flame.unsupported:
            return True
        answer = QMessageBox.question(
            self._parent, "Save fractal",
            f"'{flame.name}' uses variations Fractalchemy cannot render ({', '.join(flame.unsupported)}). "
            "They are not written, so the saved fractal will not have them. Save anyway?")
        return answer == QMessageBox.StandardButton.Yes

    def _write(self, path: Path, fn, *args, verb: str) -> bool:
        """Run a writer (after the lossy-save question); on success the document moves to the written entry and takes
        the flame's saved name. False when the user declined."""
        flame = args[0]
        if not self._confirm_lossy_save(flame):
            return False

        def done(index: int) -> None:
            self._document.rename(flame.name)
            self._document.set_source(path, index)
            self._document.mark_saved()
            self.entry_written.emit(path, index)
            self.status.emit(f"{verb} '{flame.name}' in {path.name}")

        self._run_write(path, fn, *args, on_done=done, failure_title=FAILURE_TITLE)
        return True

    def _suggested_path(self) -> Path:
        source = self._document.source_path
        flame = self._document.flame
        stem = (flame.name if flame else "") or (source.stem if source else config.APP_NAME.lower())
        folder = source.parent if source else Path(self._last_dir)
        ext = source.suffix if source and fractal_format_for(source).can_append else DEFAULT_SAVE_FORMAT.extensions[0]
        return folder / f"{stem}{ext}"


__all__ = ["FractalFileActions"]
