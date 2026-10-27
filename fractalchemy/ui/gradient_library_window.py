"""The Gradient Library window: library tree, gradient browser strip and editor, with its own File / Edit / View menus.

It is a self-contained tool window (like Apophysis's Editor / Gradient forms): the
main window shows it from *Windows ▸ Gradient Library* or the toolbar, and closing
it merely hides it — the loaded gradient and any unsaved edits are kept.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QWidget

from ..library.controller import LibraryController
from ..library.items import LibraryItem
from ..library.panel import LibraryPanel
from ..library.roots import LibraryRoots
from ..model import rgb_to_hex
from ..widgets import GradientEditor
from ..widgets.collapsible_splitter import CollapsibleSplitter
from ..widgets.fractal_preview import FractalPreview
from ..widgets.gradient_browser import GradientBrowser
from ..widgets.icons import gradient_icon
from ..widgets.node_panel import NodePanel
from ..widgets.whole_gradient_panel import WholeGradientPanel
from .document import GradientDocument
from .file_actions import FileActions
from .library_host import LibraryHost
from .loader import load_ui

WINDOW_TITLE = "Gradient Library"
UI_FILE = Path(__file__).resolve().parents[2] / "ui" / "gradient_library_window.ui"
CUSTOM_WIDGETS = {
    "FractalPreview": FractalPreview,
    "GradientBrowser": GradientBrowser,
    "GradientEditor": GradientEditor,
    "NodePanel": NodePanel,
    "WholeGradientPanel": WholeGradientPanel,
    "LibraryPanel": LibraryPanel,
    "CollapsibleSplitter": CollapsibleSplitter,
}


class GradientLibraryWindow(QMainWindow):
    """Gradient tool window: library on the left, browser / editor / panels on the right.

    Works standalone (tests) or as a child window of the main window, in which
    case it stays above it and is hidden rather than destroyed on close.
    """
    def __init__(self, roots: LibraryRoots | None = None, parent: QWidget | None = None):
        """Args:
            roots: Library folders to use; defaults to the persisted list.
            parent: Owning window; when given this becomes a child top-level window.
        """
        super().__init__(parent, Qt.WindowType.Window)
        load_ui(self, UI_FILE, CUSTOM_WIDGETS)
        self.setWindowIcon(gradient_icon())
        self.document = GradientDocument(self)
        self.gradientEditor.bind(self.document)
        self.wholeGradientPanel.bind(self.document)
        self.nodePanel.bind(self.document)
        self.files = FileActions(self.document, self)
        self.library = LibraryController(self.libraryPanel.model, roots or LibraryRoots(parent=self), self)
        self.library_host = LibraryHost(self.libraryPanel, self.library, self, self.open_item)
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
        self.actionClose.triggered.connect(self.close)
        self.actionEditLibrary.triggered.connect(self.library_host.edit)
        self.actionToggleLibrary.toggled.connect(lambda shown: self.splitter.set_collapsed(not shown))
        self.actionRefreshLibrary.triggered.connect(self.library.rescan_all)
        self.btnOpen.clicked.connect(self.files.open)
        self.btnSave.clicked.connect(self.files.save)
        self.btnSaveAs.setMenu(self.menuSaveAs)
        self.splitter.collapsed_changed.connect(lambda collapsed: self.actionToggleLibrary.setChecked(not collapsed))
        self.files.status.connect(self.statusBar().showMessage)
        self.wholeGradientPanel.status.connect(self.statusBar().showMessage)
        self.files.file_written.connect(self.library.rescan_containing)

    def _connect_document(self) -> None:
        self.document.gradient_replaced.connect(self._refresh_header)
        self.document.gradient_changed.connect(self._refresh_header)
        self.document.stop_changed.connect(self._refresh_header)
        self.files.entry_saved.connect(self._refresh_header)
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
        self.library.file_changed_externally.connect(self._on_external_change)

    # --- window management --------------------------------------------------
    def show_fractal_image(self, image) -> None:
        """Mirror the main window's viewport in the small preview beside the gradient strip."""
        self.fractalPreview.set_image(image)

    def bring_to_front(self) -> None:
        """Show the window (restoring it if minimised) and give it focus."""
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
        self.show()
        self.raise_()
        self.activateWindow()

    # --- library slots ------------------------------------------------------
    def open_item(self, item: LibraryItem) -> None:
        """Show the gradient a library row refers to, unless it is already shown."""
        if self.document.is_showing(item.path, item.index) and not self.document.modified:
            return
        if self.files.confirm_discard():
            self.files.open_path(item.path, item.index)

    def edit_library(self) -> None:
        """Open the modal Edit Library dialog (kept for the main window's menu)."""
        self.library_host.edit()

    def _on_external_change(self, path: Path) -> None:
        """Reload the open file if another program changed it and we have no unsaved edits."""
        if path == self.document.source_path and not self.document.modified and not self.files.wrote_recently(path):
            self.files.open_path(path, self.document.source_index, quiet=True)

    # --- presentation -------------------------------------------------------
    def _refresh_header(self) -> None:
        gradient = self.document.gradient
        source = self.document.source_path
        self.lblGradientName.setText(f"{gradient.name}  —  {len(gradient)} nodes" + (f"  ({source.name})" if source else ""))
        self.setWindowTitle(f"{WINDOW_TITLE} — {gradient.name}[*]" if gradient.stops else f"{WINDOW_TITLE}[*]")
        self.setWindowModified(self.document.modified)

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
