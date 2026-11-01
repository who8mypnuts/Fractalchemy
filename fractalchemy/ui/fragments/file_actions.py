"""Opening and saving fragments, parameter files and screenshots; recent files; the file watcher.

`.frag` / `.fafrag` open alike; saving writes the Fractalchemy metadata block into `.fafrag` only (`document_format`).
Saving a bundled example (the read-only library inside the package) turns into *Save as*, so the examples stay
pristine. *Save / Load parameters* handle `.fragparams` files and images that carry settings (`frAg`); *Save
screenshot* writes the viewport's image in any of the host's formats with the settings embedded. Open files are
watched: a file changed by another program is reloaded when the tab has no unsaved edits (FragM's *autoload*), else
the log says so.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6.QtCore import QFileSystemWatcher, QObject, QSettings, Signal
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from ...fragments.document_format import (PARAMS_SUFFIX, FragmentFormatError, IMAGE_KEY, read_parameters, write_fragment,
                                           write_parameters)
from ...fragments.examples import LIBRARY_DIR
from ...fragments.templates import Template
from ...render.output import FORMATS, SaveOptions, format_for_path, save_image
from .document import FragDocument
from .tabs import TabManager

FILE_FILTER = "Fragments (*.fafrag *.frag);;Fractalchemy fragment (*.fafrag);;Fragmentarium source (*.frag);;All files (*)"
PARAMS_FILTER = "Fragment parameters (*.fragparams);;Images with parameters (*.png *.jpg *.jpeg *.tif *.tiff *.exr);;All files (*)"
RECENT_KEY = "fragments/recent"
FOLDER_KEY = "fragments/folder"
SCREENSHOT_KEY = "fragments/screenshot"
DEFAULT_SUFFIX = ".fafrag"
MAX_RECENT = 10


def is_bundled(path: Path | None) -> bool:
    """True for files inside the package's example library (never overwritten)."""
    if path is None:
        return False
    try:
        Path(path).resolve().relative_to(LIBRARY_DIR.resolve())
        return True
    except ValueError:
        return False


def image_filter() -> str:
    """A file-dialog filter of every image format the host can write."""
    parts = [f"{f.label} (*{' *'.join(f.extensions)})" for f in FORMATS if f.available]
    return ";;".join(parts)


class FragmentFileActions(QObject):
    """New / open / save / parameters / screenshots for the tabs (see the module docstring).

    Signals:
        status(str): A message for the status bar.
        recent_changed(): The recent-files list changed.
        file_changed_externally(object): An open file (`Path`) changed on disk and could not be reloaded (unsaved edits).
    """
    status = Signal(str)
    recent_changed = Signal()
    file_changed_externally = Signal(object)

    def __init__(self, tabs: TabManager, window: QWidget, settings: QSettings):
        super().__init__(window)
        self.tabs = tabs
        self.window = window
        self.settings = settings
        self.autoload = True
        self.max_recent = MAX_RECENT
        self._watcher = QFileSystemWatcher(self)
        self._watcher.fileChanged.connect(self._on_file_changed)
        self._just_wrote: set[str] = set()
        tabs.document_opened.connect(self._watch)
        tabs.document_closed.connect(self._unwatch)

    # --- new ---------------------------------------------------------------------------------------------------------------
    def new_from_template(self, template: Template) -> FragDocument:
        document = self.tabs.open_text(template.text)
        self.status.emit(f"New fragment: {template.name}")
        return document

    # --- open --------------------------------------------------------------------------------------------------------------
    def open(self) -> FragDocument | None:
        """Prompt for a fragment file and open it in a tab."""
        start = self.settings.value(FOLDER_KEY, "")
        chosen, _filter = QFileDialog.getOpenFileName(self.window, "Open fragment", str(start), FILE_FILTER)
        return self.open_path(Path(chosen)) if chosen else None

    def open_path(self, path: Path) -> FragDocument | None:
        """Open `path` (or switch to its tab); bundled examples open normally but save elsewhere."""
        path = Path(path)
        try:
            document = self.tabs.open_file(path)
        except OSError as exc:
            QMessageBox.warning(self.window, "Fragments", f"Cannot read {path}:\n{exc}")
            self.status.emit(f"Cannot read {path.name}: {exc}")
            return None
        if not is_bundled(path):
            self.settings.setValue(FOLDER_KEY, str(path.parent))
            self._remember(path)
        self.status.emit(f"Opened {path.name}")
        return document

    def reload(self, document: FragDocument | None = None, ask: bool = True) -> bool:
        """Re-read a tab's file (FragM's *Reload*), asking when there are unsaved edits."""
        document = document or self.tabs.document
        if document is None or document.path is None:
            return False
        if document.modified and ask:
            answer = QMessageBox.question(self.window, "Fragments", f"Reload {document.path.name} and discard the unsaved edits?",
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
            if answer != QMessageBox.StandardButton.Yes:
                return False
        try:
            from ...fragments.document_format import read_fragment
            text, metadata = read_fragment(document.path)
        except (OSError, FragmentFormatError) as exc:
            QMessageBox.warning(self.window, "Fragments", f"Cannot read {document.path}:\n{exc}")
            return False
        if metadata is not None:
            document.metadata = metadata
        document.set_text(text, from_editor=False)
        document.mark_saved(document.path)
        self.status.emit(f"Reloaded {document.path.name}")
        return True

    # --- save --------------------------------------------------------------------------------------------------------------
    def save(self) -> bool:
        """Save the current tab (a new or bundled fragment asks for a file)."""
        document = self.tabs.document
        if document is None:
            return False
        if document.path is None or is_bundled(document.path):
            return self.save_as()
        return self._write(document, document.path)

    def save_as(self, suffix: str | None = None) -> bool:
        document = self.tabs.document
        if document is None:
            return False
        folder = Path(str(self.settings.value(FOLDER_KEY, str(Path.home()))))
        start = folder / (document.path.name if document.path else f"fragment{suffix or DEFAULT_SUFFIX}")
        if suffix and start.suffix.lower() != suffix:
            start = start.with_suffix(suffix)
        chosen, chosen_filter = QFileDialog.getSaveFileName(self.window, "Save fragment", str(start), FILE_FILTER)
        if not chosen:
            return False
        path = Path(chosen)
        if path.suffix.lower() not in (".frag", ".fafrag"):
            path = path.with_suffix(".frag" if "Fragmentarium" in chosen_filter else DEFAULT_SUFFIX)
        return self._write(document, path)

    def _write(self, document: FragDocument, path: Path) -> bool:
        try:
            self._just_wrote.add(str(path))
            write_fragment(path, document.text, document.metadata)
        except OSError as exc:
            QMessageBox.warning(self.window, "Fragments", f"Cannot write {path}:\n{exc}")
            return False
        document.mark_saved(path)
        self._watch(document)
        self.settings.setValue(FOLDER_KEY, str(path.parent))
        self._remember(path)
        self.status.emit(f"Saved {path.name}")
        return True

    # --- parameters ---------------------------------------------------------------------------------------------------------
    def save_parameters(self) -> bool:
        """*Parameters ▸ Save to file*: the settings text as `.fragparams`."""
        document = self.tabs.document
        if document is None:
            return False
        start = Path(str(self.settings.value(FOLDER_KEY, str(Path.home())))) / f"{document.name}{PARAMS_SUFFIX}"
        chosen, _filter = QFileDialog.getSaveFileName(self.window, "Save parameters", str(start), PARAMS_FILTER)
        if not chosen:
            return False
        path = Path(chosen)
        if not path.suffix:
            path = path.with_suffix(PARAMS_SUFFIX)
        try:
            write_parameters(path, document.state.to_text(provenance=document.path.name if document.path else "Unnamed"))
        except OSError as exc:
            QMessageBox.warning(self.window, "Fragments", f"Cannot write {path}:\n{exc}")
            return False
        self.status.emit(f"Settings saved to {path.name}")
        return True

    def load_parameters(self, path: Path | None = None) -> bool:
        """*Parameters ▸ Load from file*: a `.fragparams` file or an image carrying settings."""
        document = self.tabs.document
        if document is None:
            return False
        if path is None:
            start = str(self.settings.value(FOLDER_KEY, ""))
            chosen, _filter = QFileDialog.getOpenFileName(self.window, "Load parameters", start, PARAMS_FILTER)
            if not chosen:
                return False
            path = Path(chosen)
        try:
            text = read_parameters(path)
        except (OSError, FragmentFormatError, ValueError) as exc:
            QMessageBox.warning(self.window, "Fragments", f"Cannot read settings from {path}:\n{exc}")
            return False
        document.apply_settings(text, path.name)
        self.status.emit(f"Settings loaded from {path.name}")
        return True

    # --- screenshots ------------------------------------------------------------------------------------------------------------
    def save_screenshot(self, image: QImage | None) -> bool:
        """Write the viewport's image with the settings embedded (FragM's *Save Screen Shot*)."""
        document = self.tabs.document
        if document is None or image is None or image.isNull():
            self.status.emit("Nothing rendered yet")
            return False
        start = Path(str(self.settings.value(SCREENSHOT_KEY, self.settings.value(FOLDER_KEY, str(Path.home()))))) / f"{document.name}.png"
        chosen, _filter = QFileDialog.getSaveFileName(self.window, "Save screenshot", str(start), image_filter())
        if not chosen:
            return False
        path = Path(chosen)
        fmt = format_for_path(path)
        if fmt is None:
            path = path.with_suffix(".png")
            fmt = format_for_path(path)
        settings_text = document.state.to_text(provenance=document.path.name if document.path else "Unnamed")
        try:
            save_image(qimage_to_rgba16(image), path, fmt, SaveOptions(parameters=settings_text, parameters_key=IMAGE_KEY))
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self.window, "Fragments", f"Cannot write {path}:\n{exc}")
            return False
        self.settings.setValue(SCREENSHOT_KEY, str(path.parent))
        self.status.emit(f"Saved screenshot {path.name}")
        return True

    # --- the watcher ------------------------------------------------------------------------------------------------------------
    def _watch(self, document: FragDocument) -> None:
        if document.path is not None and document.path.is_file() and not is_bundled(document.path):
            self._watcher.addPath(str(document.path))

    def _unwatch(self, document: FragDocument) -> None:
        if document.path is not None and str(document.path) in self._watcher.files():
            if not any(t.document.path == document.path for t in self.tabs.tabs if t.document is not document):
                self._watcher.removePath(str(document.path))

    def _on_file_changed(self, name: str) -> None:
        path = Path(name)
        if name in self._just_wrote:
            self._just_wrote.discard(name)
            return
        tab = self.tabs.tab_for_path(path)
        if tab is None or not path.is_file():
            return
        if tab.document.modified or not self.autoload:
            self.file_changed_externally.emit(path)
            self.status.emit(f"{path.name} changed on disk (not reloaded: unsaved edits)" if tab.document.modified else f"{path.name} changed on disk")
        elif self.reload(tab.document, ask=False):
            self.status.emit(f"{path.name} changed on disk — reloaded")
        if name not in self._watcher.files():            # editors that replace the file drop it from the watch list
            self._watcher.addPath(name)

    # --- recent files -------------------------------------------------------------------------------------------------------
    def recent(self) -> list[Path]:
        value = self.settings.value(RECENT_KEY, [])
        if isinstance(value, str):
            value = [value]
        return [Path(p) for p in (value or []) if p]

    def _remember(self, path: Path) -> None:
        recent = [p for p in self.recent() if p != path]
        recent.insert(0, path)
        self.settings.setValue(RECENT_KEY, [str(p) for p in recent[:self.max_recent]])
        self.recent_changed.emit()

    def confirm_close_all(self) -> bool:
        """Ask about every unsaved tab before the window closes; False = keep them open."""
        unsaved = self.tabs.unsaved_documents()
        if not unsaved:
            return True
        names = ", ".join(d.path.name if d.path else "Unnamed" for d in unsaved)
        answer = QMessageBox.warning(self.window, "Fragments", f"There are unsaved changes ({names}).\nContinue and discard them?",
                                     QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        return answer == QMessageBox.StandardButton.Discard


def qimage_to_rgba16(image: QImage) -> np.ndarray:
    """A QImage as the (H, W, 4) uint16 RGBA array the image writers take."""
    converted = image.convertToFormat(QImage.Format.Format_RGBA8888)
    width, height = converted.width(), converted.height()
    buffer = converted.constBits()
    data = np.frombuffer(buffer, dtype=np.uint8, count=converted.sizeInBytes()).reshape(height, converted.bytesPerLine())[:, :width * 4]
    return (data.reshape(height, width, 4).astype(np.uint16) * 257)


__all__ = ["FragmentFileActions", "is_bundled", "image_filter", "qimage_to_rgba16", "FILE_FILTER", "DEFAULT_SUFFIX"]
