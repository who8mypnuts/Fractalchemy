"""Open / Save / Save As, driving a GradientDocument through file dialogs."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from .. import config
from ..formats import (
    DEFAULT_SAVE_FORMAT,
    FormatError,
    load_gradient,
    open_dialog_filter,
    save_dialog_filter,
    save_gradient,
)
from .document import GradientDocument


class FileActions(QObject):
    status = Signal(str)  # short human-readable outcome, e.g. for the status bar

    def __init__(self, document: GradientDocument, parent: QWidget):
        super().__init__(parent)
        self._document = document
        self._parent = parent
        self._last_dir = str(Path.cwd())

    # --- public slots -------------------------------------------------------
    def open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self._parent, "Open gradient source", self._last_dir, open_dialog_filter())
        if path:
            self.open_path(Path(path))

    def open_path(self, path: Path) -> None:
        try:
            gradient = load_gradient(path)
        except (FormatError, OSError, ValueError) as exc:
            return self._fail("Could not open file", exc)
        self._remember(path)
        self._document.replace(gradient, path)
        self.status.emit(f"Loaded '{gradient.name}' from {path.name} ({len(gradient)} nodes)")

    def save(self) -> None:
        target = self._writable_source_path()
        if target is None:
            return self.save_as()
        self._write(target)

    def save_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self._parent, "Save gradient", str(self._suggested_save_path()), save_dialog_filter()
        )
        if path:
            self._write(Path(path))

    # --- helpers ------------------------------------------------------------
    def _write(self, path: Path) -> None:
        try:
            save_gradient(self._document.gradient, path)
        except (FormatError, OSError) as exc:
            return self._fail("Could not save file", exc)
        self._remember(path)
        self._document.mark_saved(path)
        self.status.emit(f"Saved '{self._document.gradient.name}' to {path.name}")

    def _writable_source_path(self) -> Path | None:
        fmt = self._document.source_format
        return self._document.source_path if fmt is not None and fmt.can_save else None

    def _suggested_save_path(self) -> Path:
        source = self._document.source_path
        if self._writable_source_path() is not None:
            return source  # type: ignore[return-value]
        ext = DEFAULT_SAVE_FORMAT.extensions[0]
        stem = source.stem if source else self._document.gradient.name or config.APP_NAME.lower()
        return Path(self._last_dir) / f"{stem}{ext}"

    def _remember(self, path: Path) -> None:
        self._last_dir = str(path.parent)

    def _fail(self, title: str, exc: Exception) -> None:
        QMessageBox.warning(self._parent, title, str(exc))
        self.status.emit(f"{title}: {exc}")
