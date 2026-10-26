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

import time
from datetime import date
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QWidget

from ..fractal.formats import (
    DEFAULT_SAVE_FORMAT, FORMATS, fractal_format_for, load_flame, open_dialog_filter, save_dialog_filter,
)
from ..fractal.formats.clipboard import ClipboardError, flame_to_text, text_to_flames
from ..fractal.scene import Flame
from .background import run_in_background
from .fractal_document import FractalDocument

RECENT_WRITE_SECONDS = 3.0


class FractalFileActions(QObject):
    """File and clipboard flows for a FractalDocument.

    Signals:
        status(str): Outcome text for the status bar.
        file_written(Path): A file on disk changed because of us.
        file_opened(Path): A file was opened or created through these actions (the library shows it).
    """
    status = Signal(str)
    file_written = Signal(Path)
    file_opened = Signal(Path)

    def __init__(self, document: FractalDocument, parent: QWidget):
        super().__init__(parent)
        self._document = document
        self._parent = parent
        self._last_dir = str(Path.cwd())
        self._load_ticket = 0
        self._written: dict[Path, float] = {}

    # --- opening ------------------------------------------------------------
    def open(self) -> None:
        """Prompt for a fractal file and show its first flame (after checking for unsaved edits)."""
        if not self.confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(self._parent, "Open fractal", self._last_dir, open_dialog_filter())
        if path:
            self.open_path(Path(path), 0, announce=True)

    def open_path(self, path: Path, index: int = 0, announce: bool = False, note: str | None = None) -> None:
        """Load flame `index` of `path` on a worker thread, then show it.

        `announce` emits `file_opened` so the library lists the file's flames.
        """
        self._load_ticket += 1
        ticket = self._load_ticket
        self.status.emit(f"Loading {path.name}…")
        run_in_background(load_flame, path, index,
                          on_done=lambda flame: self._loaded(flame, path, index, ticket, announce, note),
                          on_error=lambda exc: self._fail("Could not open fractal", exc))

    def _loaded(self, flame: Flame, path: Path, index: int, ticket: int, announce: bool, note: str | None) -> None:
        if ticket != self._load_ticket:
            return
        self._last_dir = str(path.parent)
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
                        on_done=lambda _: self._saved(snapshot, path, index))
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
        name = self._ask_name()
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
                        on_done=lambda result: self._saved(snapshot, path, result[0], opened=True, note=result[1]))
        return True


    def save_as_into_file(self) -> bool:
        """Pick an existing `.fa` / `.flame` file and append the flame to it under a chosen name.

        Returns:
            True if a write was started.
        """
        if self._document.flame is None:
            return False
        chosen, _ = QFileDialog.getOpenFileName(self._parent, "Add fractal to an existing file", self._last_dir, _append_filter())
        name = self._ask_name() if chosen else None
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
                        on_done=lambda index: self._saved(snapshot, path, index, opened=True, renamed=True))

    def _ask_name(self) -> str | None:
        name, ok = QInputDialog.getText(self._parent, "Fractal name", "Save fractal as:", text=self._document.flame.name)
        return name.strip() if ok and name.strip() else None

    def confirm_discard(self) -> bool:
        """Ask about unsaved edits before replacing the flame. Returns False if the caller should abort."""
        if not self._document.modified:
            return True
        buttons = QMessageBox.StandardButton
        answer = QMessageBox.question(
            self._parent, "Unsaved changes", f"'{self._document.flame.name}' has unsaved changes.",
            buttons.Save | buttons.Discard | buttons.Cancel, buttons.Save)
        if answer == buttons.Save:
            return self.save()
        return answer == buttons.Discard

    def wrote_recently(self, path: Path) -> bool:
        """True if we wrote `path` within the last few seconds (to ignore our own watcher events)."""
        return time.monotonic() - self._written.get(path, -1e9) < RECENT_WRITE_SECONDS

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

    def _run_write(self, path: Path, fn, *args, on_done) -> None:
        def done(result) -> None:
            self._written[path] = time.monotonic()
            self._last_dir = str(path.parent)
            on_done(result)
            self.file_written.emit(path)

        self._written[path] = time.monotonic()   # before the write too: the watcher can fire before `done`
        run_in_background(fn, *args, on_done=done, on_error=lambda exc: self._fail("Could not save fractal", exc))

    def _saved(self, snapshot: Flame, path: Path, index: int, opened: bool = False, note: str = "", renamed: bool = False) -> None:
        current = self._document.flame
        if current is not None:
            same = current.to_dict() == snapshot.to_dict() if not renamed else {**current.to_dict(), "name": snapshot.name} == snapshot.to_dict()
            if same:
                if renamed:
                    current.name = snapshot.name   # the document now *is* the entry it was saved as
                self._document.mark_saved(path, index)
                if renamed:
                    self._document.flame_renamed.emit()
        if opened:
            self.file_opened.emit(path)
        self.status.emit(note or f"Saved '{snapshot.name}' to {path.name}")

    def _suggested_path(self) -> Path:
        """`FA-YYMMDD-N.fa` in the current folder, N being the first number not yet used (Apophysis-style)."""
        source = self._document.source_path
        folder = source.parent if source is not None else Path(self._last_dir)
        return suggested_file_name(folder, DEFAULT_SAVE_FORMAT.extensions[0])

    def _fail(self, title: str, exc: Exception) -> None:
        QMessageBox.warning(self._parent, title, str(exc))
        self.status.emit(f"{title}: {exc}")


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
