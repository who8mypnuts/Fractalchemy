"""Top-level window: loads the Designer layout and wires library, editor and file actions."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox

from .. import config
from ..library.context_menu import LibraryContextMenu
from ..library.controller import LibraryController
from ..library.dialog import EditLibraryDialog
from ..library.items import LibraryItem
from ..library.panel import LibraryPanel
from ..library.roots import LibraryRoots
from ..model import rgb_to_hex
from ..widgets import GradientEditor
from ..widgets.collapsible_splitter import CollapsibleSplitter
from ..widgets.gradient_browser import GradientBrowser
from ..widgets.node_panel import NodePanel
from ..widgets.whole_gradient_panel import WholeGradientPanel
from .document import GradientDocument
from .file_actions import FileActions
from .loader import load_ui

SCANNING_MESSAGE = "Scanning library…"
UI_FILE = Path(__file__).resolve().parents[2] / "ui" / "main_window.ui"
CUSTOM_WIDGETS = {
    "GradientBrowser": GradientBrowser,
    "GradientEditor": GradientEditor,
    "NodePanel": NodePanel,
    "WholeGradientPanel": WholeGradientPanel,
    "LibraryPanel": LibraryPanel,
    "CollapsibleSplitter": CollapsibleSplitter,
}


class MainWindow(QMainWindow):
    def __init__(self, roots: LibraryRoots | None = None):
        super().__init__()
        load_ui(self, UI_FILE, CUSTOM_WIDGETS)
        self.document = GradientDocument(self)
        self.gradientEditor.bind(self.document)
        self.wholeGradientPanel.bind(self.document)
        self.nodePanel.bind(self.document)
        self.files = FileActions(self.document, self)
        self.library = LibraryController(self.libraryPanel.model, roots or LibraryRoots(parent=self), self)
        self.library_menu = LibraryContextMenu(self.library, self.open_item, self)
        self._connect_actions()
        self._connect_document()
        self._connect_browser()
        self._connect_library()
        self._refresh_save_targets()
        self.library.rescan_all()

    # --- wiring -------------------------------------------------------------
    def _connect_actions(self) -> None:
        self.actionOpen.triggered.connect(self.files.open)
        self.actionSave.triggered.connect(self.files.save)
        self.actionSaveAsNewEntry.triggered.connect(self.files.save_as_new_entry)
        self.actionSaveAsNewFile.triggered.connect(self.files.save_as_new_file)
        self.actionSaveAsIntoFile.triggered.connect(self.files.save_as_into_file)
        self.actionExit.triggered.connect(self.close)
        self.actionEditLibrary.triggered.connect(self.edit_library)
        self.actionToggleLibrary.toggled.connect(lambda shown: self.splitter.set_collapsed(not shown))
        self.actionRefreshLibrary.triggered.connect(self.library.rescan_all)
        self.btnOpen.clicked.connect(self.files.open)
        self.btnSave.clicked.connect(self.files.save)
        self.btnSaveAs.setMenu(self.menuSaveAs)
        self.splitter.collapsed_changed.connect(lambda collapsed: self.actionToggleLibrary.setChecked(not collapsed))
        self.files.status.connect(self.statusBar().showMessage)
        self.files.file_written.connect(self.library.rescan_containing)

    def _connect_document(self) -> None:
        self.document.gradient_replaced.connect(self._refresh_header)
        self.document.gradient_changed.connect(self._refresh_header)
        self.document.gradient_replaced.connect(self._refresh_save_targets)
        self.document.stop_changed.connect(self._show_stop)
        self.document.selection_changed.connect(self._show_stop)

    def _connect_browser(self) -> None:
        browser = self.gradientBrowser
        self.files.entries_loaded.connect(browser.set_entries)
        self.files.entry_saved.connect(browser.update_entry)
        self.document.gradient_replaced.connect(lambda: browser.set_current(self.document.source_index))
        browser.entry_chosen.connect(self.files.show_entry)

    def _connect_library(self) -> None:
        panel = self.libraryPanel
        panel.add_requested.connect(self.add_library_folder)
        panel.edit_requested.connect(self.edit_library)
        panel.item_chosen.connect(self.open_item)
        panel.menu_requested.connect(lambda item, pos: self.library_menu.show(item, panel.tree.selected_items(), pos))
        self.library.status.connect(self.statusBar().showMessage)
        self.library.failed.connect(self._report_library_error)
        self.library.file_changed_externally.connect(self._on_external_change)
        self.library.scanning.connect(self._show_scanning)

    # --- library slots ------------------------------------------------------
    def open_item(self, item: LibraryItem) -> None:
        if self.document.is_showing(item.path, item.index) and not self.document.modified:
            return
        if self.files.confirm_discard():
            self.files.open_path(item.path, item.index)

    def add_library_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Add folder to library")
        if folder and not self.library.roots.add(Path(folder)):
            self.statusBar().showMessage("That folder is already in the library")

    def edit_library(self) -> None:
        EditLibraryDialog(self.library, self.add_library_folder, self).exec()

    def _show_scanning(self, busy: bool) -> None:
        if busy:
            self.statusBar().showMessage(SCANNING_MESSAGE)
        elif self.statusBar().currentMessage() == SCANNING_MESSAGE:
            self.statusBar().clearMessage()

    def _on_external_change(self, path: Path) -> None:
        """Reload the open file if another program changed it and we have no unsaved edits."""
        if path == self.document.source_path and not self.document.modified and not self.files.wrote_recently(path):
            self.files.open_path(path, self.document.source_index)

    def _report_library_error(self, message: str) -> None:
        self.statusBar().showMessage(message)
        QMessageBox.warning(self, "Library", message)

    # --- presentation -------------------------------------------------------
    def _refresh_header(self) -> None:
        gradient = self.document.gradient
        source = self.document.source_path
        self.lblGradientName.setText(f"{gradient.name}  —  {len(gradient)} nodes" + (f"  ({source.name})" if source else ""))
        self.setWindowTitle(f"{config.APP_NAME} — {gradient.name}" if gradient.stops else config.APP_NAME)

    def _refresh_save_targets(self) -> None:
        fmt = self.document.source_format
        has_gradient = bool(self.document.gradient.stops)
        self.btnSave.setEnabled(has_gradient)
        self.btnSaveAs.setEnabled(has_gradient)
        self.actionSave.setEnabled(has_gradient)
        self.actionSaveAsNewEntry.setEnabled(has_gradient and fmt is not None and fmt.can_append)
        self.btnSave.setToolTip(
            f"Write back into {self.document.source_path.name}" if fmt is not None and fmt.can_save
            else "Save to a new file (this source can't be written)"
        )

    def _show_stop(self, index: int) -> None:
        stops = self.document.gradient.stops
        if 0 <= index < len(stops):
            stop = stops[index]
            self.statusBar().showMessage(f"Node {index + 1}/{len(stops)}  position {stop.position:.3f}  #{rgb_to_hex(stop.color)}")
