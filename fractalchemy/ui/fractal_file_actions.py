"""Open / Save / Save As / Copy / Paste for the fractal shown in the main window.

Disk work runs on the thread pool. **Save** writes the flame back into its own entry when
the file type allows it (`.fa`, `.flame`). **Save As** has the same three flavours as the
Gradient Library, so one `.fa` (or `.flame`) file can collect many fractals:

* *Add to This File as New Fractal…* — append to the flame's own file under a name you choose;
* *New File…* — a new file in any format (Fractalchemy `.fa` by default; an existing
  multi-flame file is appended to, never wiped);
* *Add to Another File…* — pick an existing file and append under a chosen name.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from ..fractal.formats import (
    DEFAULT_SAVE_FORMAT, FORMATS, fractal_format_for, load_flame, open_dialog_filter, save_dialog_filter,
)
from ..fractal.formats.clipboard import ClipboardError, flame_to_text, text_to_flames
from ..fractal.scene import Flame
from .background import run_in_background
from .file_actions_base import FileActionsBase
from .fractal_document import FractalDocument


class FractalFileActions(FileActionsBase):
    """File and clipboard flows for a FractalDocument.

    Signals (besides the base class's `status` / `file_written`):
        file_opened(Path): A file was opened or created through these actions (the library shows it).
    """
    file_opened = Signal(Path)

    def __init__(self, document: FractalDocument, parent: QWidget):
        super().__init__(parent)
        self._document = document

    def _document_name(self) -> str:
        return self._document.flame.name if self._document.flame is not None else ""

    def _document_modified(self) -> bool:
        return self._document.modified

    # --- opening ------------------------------------------------------------
    def open(self) -> None:
        """Prompt for a fractal file and show its first flame (after checking for unsaved edits)."""
        if not self.confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(self._parent, "Open fractal", self._last_dir, open_dialog_filter())
        if path:
            self.open_path(Path(path), 0, announce=True)

    def open_path(self, path: Path, index: int = 0, announce: bool = False, note: str | None = None,
                  quiet: bool = False) -> None:
        """Load flame `index` of `path` on a worker thread, then show it.

        Args:
            path: The file.
            index: Which flame in it.
            announce: Emit `file_opened` so the library lists the file's flames.
            note: Status text instead of the usual "Loaded …".
            quiet: Report failure on the status bar only (for reloads nobody asked for, e.g. after a
                file watcher event that may have caught the file mid-write).
        """
        ticket = self._next_load_ticket()
        self.status.emit(f"Loading {path.name}…")
        run_in_background(load_flame, path, index,
                          on_done=lambda flame: self._loaded(flame, path, index, ticket, announce, note),
                          on_error=lambda exc: self._fail("Could not open fractal", exc, quiet))

    def _loaded(self, flame: Flame, path: Path, index: int, ticket: int, announce: bool, note: str | None) -> None:
        if not self._is_current_ticket(ticket):
            return
        self._remember(path)
        self._document.replace(flame, path, index)
        if announce:
            self.file_opened.emit(path)
        self.status.emit(note or f"Loaded '{flame.name}' from {path.name}")

    # --- saving -------------------------------------------------------------
    def save(self) -> bool:
        """Write the flame back into its own entry, or fall through to Save As.

        Returns:
            True if a write was started.
        """
        path, index = self._document.source_path, self._document.source_index
        flame = self._document.flame
        if flame is None:
            return False
        fmt = _format_or_none(path)
        if path is None or fmt is None or not fmt.can_replace:
            return self.save_as_new_file()
        if flame.unsupported and not self._confirm_lossy_save(path, flame):
            return False
        snapshot = flame.copy()
        self._run_write(path, fmt.replace, snapshot, path, index,
                        on_done=lambda _: self._saved(snapshot, path, index), failure_title="Could not save fractal")
        return True

    def save_as_new_entry(self) -> bool:
        """Append the flame to its own file under a (possibly new) name; falls back to 'another file'.

        Returns:
            True if a write was started.
        """
        path = self._document.source_path
        fmt = _format_or_none(path)
        if path is None or fmt is None or not fmt.can_append:
            return self.save_as_into_file()
        name = self._ask_name("fractal", self._document.flame.name)
        if not name:
            return False
        self._append_to(path, name)
        return True

    def save_as_new_file(self) -> bool:
        """Prompt for a file (any format, `.fa` by default) and write the flame there.

        An existing `.fa` / `.flame` file gains the flame as a new entry; other targets are
        (re)written as a file holding just this flame.

        Returns:
            True if a write was started.
        """
        flame = self._document.flame
        if flame is None:
            return False
        chosen, _ = QFileDialog.getSaveFileName(self._parent, "Save fractal as new file", str(self._suggested_path()),
                                                save_dialog_filter(), DEFAULT_SAVE_FORMAT.dialog_filter())
        if not chosen:
            return False
        path = Path(chosen)
        if not path.suffix:
            path = path.with_suffix(DEFAULT_SAVE_FORMAT.extensions[0])
        fmt = _format_or_none(path)
        if fmt is None:
            self._fail("Could not save", ValueError(f"Unknown fractal file type '{path.suffix}'"))
            return False
        snapshot = flame.copy()
        self._run_write(path, _write_as, snapshot, path, fmt,
                        on_done=lambda result: self._saved(snapshot, path, result[0], opened=True, note=result[1]),
                        failure_title="Could not save fractal")
        return True


    def save_as_into_file(self) -> bool:
        """Pick an existing `.fa` / `.flame` file and append the flame to it under a chosen name.

        Returns:
            True if a write was started.
        """
        if self._document.flame is None:
            return False
        chosen, _ = QFileDialog.getOpenFileName(self._parent, "Add fractal to an existing file", self._last_dir, _append_filter())
        name = self._ask_name("fractal", self._document.flame.name) if chosen else None
        if not name:
            return False
        self._append_to(Path(chosen), name)
        return True

    def _append_to(self, path: Path, name: str) -> None:
        fmt = _format_or_none(path)
        if fmt is None or not fmt.can_append:
            self._fail("Could not save", ValueError(f"Fractals cannot be added to {path.suffix or path.name} files"))
            return
        snapshot = self._document.flame.copy()
        snapshot.name = name
        self._run_write(path, _append, snapshot, path, fmt,
                        on_done=lambda index: self._saved(snapshot, path, index, opened=True, renamed=True),
                        failure_title="Could not save fractal")

    # --- clipboard ----------------------------------------------------------
    def copy(self, fmt: str = "fa") -> bool:
        """Put the flame on the clipboard as text: 'fa' (default), 'flame' (Apophysis) or 'chaos' (Chaotica)."""
        flame = self._document.flame
        if flame is None:
            return False
        QGuiApplication.clipboard().setText(flame_to_text(flame, fmt))
        self.status.emit({"fa": "Copied parameters", "flame": "Copied Apophysis parameters",
                          "chaos": "Copied Chaotica parameters"}[fmt])
        return True

    def paste(self) -> bool:
        """Show the flame on the clipboard (Fractalchemy, Apophysis or Chaotica text) as a new, unsaved fractal."""
        try:
            flames = text_to_flames(QGuiApplication.clipboard().text())
        except ClipboardError as exc:
            self._fail("Nothing to paste", exc)
            return False
        if not flames or not self.confirm_discard():
            return False
        self._document.replace(flames[0])
        extra = f" (first of {len(flames)})" if len(flames) > 1 else ""
        self.status.emit(f"Pasted '{flames[0].name}'{extra}")
        return True

    # --- helpers ------------------------------------------------------------
    def _confirm_lossy_save(self, path: Path, flame: Flame) -> bool:
        names = ", ".join(flame.unsupported)
        box = QMessageBox(QMessageBox.Icon.Warning, "Unsupported variations",
                          f"'{flame.name}' uses variations Fractalchemy cannot render yet ({names}).\n\n"
                          f"Saving it back into {path.name} will drop them. Save anyway?", parent=self._parent)
        save = box.addButton("Save anyway", QMessageBox.ButtonRole.AcceptRole)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.exec()
        return box.clickedButton() is save

    def _saved(self, snapshot: Flame, path: Path, index: int, opened: bool = False, note: str = "", renamed: bool = False) -> None:
        """A write finished: re-point the document at the saved entry if the user has not moved on meanwhile.

        `renamed` means the entry was saved under `snapshot.name`; the document takes that name.
        """
        if self._is_still(snapshot, ignore_name=renamed):
            if renamed:
                self._document.flame.name = snapshot.name
                self._document.flame_renamed.emit()
            self._document.mark_saved(path, index)
        if opened:
            self.file_opened.emit(path)
        self.status.emit(note or f"Saved '{snapshot.name}' to {path.name}")

    def _is_still(self, snapshot: Flame, ignore_name: bool) -> bool:
        """True if the document still holds exactly what was written (edits since the save would be lost otherwise)."""
        current = self._document.flame
        if current is None:
            return False
        ours, theirs = current.to_dict(), snapshot.to_dict()
        if ignore_name:
            ours["name"] = theirs["name"]
        return ours == theirs

    def _suggested_path(self) -> Path:
        """`FA-YYMMDD-N.fa` in the current folder, N being the first number not yet used (Apophysis-style)."""
        source = self._document.source_path
        folder = source.parent if source is not None else Path(self._last_dir)
        return suggested_file_name(folder, DEFAULT_SAVE_FORMAT.extensions[0])


def _write_as(flame: Flame, path: Path, fmt) -> tuple[int, str]:
    """'New file' on the worker thread: append to an existing multi-flame file (never wipe it), else write a new one.

    Returns:
        (entry index, status note or '').
    """
    if path.exists() and fmt.can_append:
        index = fmt.append(flame, path)
        return index, f"{path.name} exists — added '{flame.name}' to it instead of replacing the file"
    fmt.write_file([flame], path)
    return 0, ""


def _append(flame: Flame, path: Path, fmt) -> int:
    """Append on the worker thread (creating the file if needed). Returns the new entry's index."""
    return fmt.append(flame, path)


def _append_filter() -> str:
    """Dialog filter for formats a fractal can be added to."""
    return ";;".join(f.dialog_filter() for f in FORMATS if f.can_append)


def _format_or_none(path: Path | None):
    if path is None:
        return None
    try:
        return fractal_format_for(path)
    except ValueError:
        return None


FILE_PREFIX = "FA"


def suggested_file_name(folder: Path, suffix: str, today: date | None = None) -> Path:
    """`FA-YYMMDD-N<suffix>` in `folder`, with the lowest N that does not exist yet."""
    stamp = (today or date.today()).strftime("%y%m%d")
    n = 1
    while (folder / f"{FILE_PREFIX}-{stamp}-{n}{suffix}").exists():
        n += 1
    return folder / f"{FILE_PREFIX}-{stamp}-{n}{suffix}"
