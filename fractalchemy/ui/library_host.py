"""Everything a window does to host a library pane — shared by the main window and the Gradient Library.

    host = LibraryHost(panel, controller, window, open_item=window.open_item)

Wires the panel's buttons and tree to the controller, owns the context menu, prompts
for folders, opens the Edit Library dialog, and reports scanning / status / errors on
the window's status bar.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox

from ..library.context_menu import LibraryContextMenu
from ..library.controller import LibraryController
from ..library.dialog import EditLibraryDialog
from ..library.items import LibraryItem
from ..library.panel import LibraryPanel


class LibraryHost(QObject):
    """Binds a LibraryPanel and its LibraryController to the window that shows them."""

    def __init__(self, panel: LibraryPanel, controller: LibraryController, window: QMainWindow,
                 open_item: Callable[[LibraryItem], None], message_ms: int = 0):
        """Args:
            panel: The pane with the tree and buttons.
            controller: Scans roots and runs file operations for the pane.
            window: Owns dialogs and the status bar messages go to.
            open_item: Called when the user chooses a file or entry row.
            message_ms: How long status messages stay (0 = until replaced).
        """
        super().__init__(window)
        self.panel = panel
        self.controller = controller
        self.window = window
        self.menu = LibraryContextMenu(controller, open_item, window)
        self._message_ms = message_ms
        self._scanning_message = f"Scanning {controller.catalog.title.lower()}…"
        panel.add_requested.connect(self.add_folder)
        panel.edit_requested.connect(self.edit)
        panel.item_chosen.connect(open_item)
        panel.menu_requested.connect(lambda item, pos: self.menu.show(item, panel.tree.selected_items(), pos))
        controller.status.connect(self.message)
        controller.failed.connect(self.report_error)
        controller.scanning.connect(self._show_scanning)

    def add_folder(self) -> None:
        """Prompt for a folder and add it to the library."""
        title = self.controller.catalog.title.lower()
        folder = QFileDialog.getExistingDirectory(self.window, f"Add folder to the {title}")
        if folder and not self.controller.roots.add(Path(folder)):
            self.message(f"That folder is already in the {title}")

    def edit(self) -> None:
        """Open the modal Edit Library dialog."""
        EditLibraryDialog(self.controller, self.add_folder, self.window).exec()

    def message(self, text: str) -> None:
        """Show `text` on the window's status bar."""
        self.window.statusBar().showMessage(text, self._message_ms)

    def report_error(self, text: str) -> None:
        """Show `text` on the status bar and in a warning box."""
        self.message(text)
        QMessageBox.warning(self.window, self.controller.catalog.title, text)

    def _show_scanning(self, busy: bool) -> None:
        bar = self.window.statusBar()
        if busy:
            bar.showMessage(self._scanning_message)
        elif bar.currentMessage() == self._scanning_message:
            bar.clearMessage()
