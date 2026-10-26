"""Right-click menu for tree items. Gathers user input, then calls the controller."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QPoint
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QInputDialog, QMenu, QMessageBox, QWidget

from .controller import LibraryController
from .items import Kind, LibraryItem


class LibraryContextMenu:
    """Builds and shows the right-click menu for library rows."""
    def __init__(self, controller: LibraryController, open_item: Callable[[LibraryItem], None], parent: QWidget):
        """Args:
            controller: Executes the chosen operations.
            open_item: Called with the item when 'Open' is chosen.
            parent: Widget that owns the menu and any prompts.
        """
        self._controller = controller
        self._open_item = open_item
        self._parent = parent

    def show(self, item: LibraryItem | None, selection: list[LibraryItem], pos: QPoint) -> None:
        """Show the menu for `item` at global `pos`; `selection` feeds multi-item actions."""
        menu = QMenu(self._parent)
        if item is None:
            self._add(menu, "Refresh", self._controller.rescan_all)
        else:
            self._populate(menu, item, selection if item in selection else [item])
        menu.exec(pos)

    # --- menu composition ---------------------------------------------------
    def _populate(self, menu: QMenu, item: LibraryItem, selection: list[LibraryItem]) -> None:
        ctl = self._controller
        if item.opens_entry:
            self._add(menu, "Open", lambda: self._open_item(item))
            menu.addSeparator()
        if item.kind in (Kind.FILE, Kind.ENTRY):
            self._add(menu, "Copy", lambda: ctl.copy_to_clipboard(selection))
        if item.kind != Kind.ENTRY:
            self._add(menu, "Paste", lambda: ctl.paste(item))
        if item.kind in (Kind.FILE, Kind.ENTRY):
            self._add(menu, "Duplicate", lambda: ctl.duplicate(item))
        if item.kind != Kind.ROOT:
            self._add(menu, "Rename…", lambda: self._rename(item))
            self._add(menu, "Delete…", lambda: self._delete(selection))
        menu.addSeparator()
        if item.is_directory:
            self._add(menu, "New Folder…", lambda: self._new_folder(item))
        self._add(menu, "Show in File Manager", lambda: ctl.reveal(item))
        self._add(menu, "Refresh", lambda: ctl.rescan_containing(item.path))
        if item.kind == Kind.ROOT:
            menu.addSeparator()
            self._add(menu, "Remove from Library", lambda: ctl.remove_root(item.path))

    def _add(self, menu: QMenu, text: str, handler) -> QAction:
        action = menu.addAction(text)
        action.triggered.connect(handler)
        return action

    # --- prompts ------------------------------------------------------------
    def _rename(self, item: LibraryItem) -> None:
        label = f"{self._controller.catalog.entry_label.capitalize()} name:" if item.kind == Kind.ENTRY else "File name:"
        name, ok = QInputDialog.getText(self._parent, "Rename", label, text=item.name)
        if ok and name.strip() and name.strip() != item.name:
            self._controller.rename(item, name.strip())

    def _new_folder(self, item: LibraryItem) -> None:
        name, ok = QInputDialog.getText(self._parent, "New Folder", "Folder name:", text="New Folder")
        if ok and name.strip():
            self._controller.new_folder(item, name.strip())

    def _delete(self, items: list[LibraryItem]) -> None:
        what = items[0].name if len(items) == 1 else f"{len(items)} items"
        answer = QMessageBox.question(self._parent, "Delete", f"Delete {what}?",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            self._controller.delete(items)
