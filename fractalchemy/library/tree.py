"""The QTreeView: selection → gradient requests, context-menu requests, expansion memory."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QModelIndex, QPoint, Qt, QTimer, Signal
from PySide6.QtWidgets import QAbstractItemView, QTreeView

from .filter import LibraryFilter
from .items import LibraryItem
from .model import LibraryModel


class LibraryTree(QTreeView):
    """The library QTreeView.

    Signals:
        item_chosen(LibraryItem): The current row changed to a file or gradient entry.
        menu_requested(LibraryItem | None, QPoint): Right-click at a global position.
    """
    item_chosen = Signal(object)
    menu_requested = Signal(object, QPoint)

    def __init__(self, model: LibraryModel, parent=None):
        """Wrap `model` in a search proxy and configure drag/drop and selection."""
        super().__init__(parent)
        self._model = model
        self._proxy = LibraryFilter(self)
        self._proxy.setSourceModel(model)
        self._expanded: set[Path] = set()
        self._seen_roots: set[Path] = set()
        self.setModel(self._proxy)
        self._configure()
        self.selectionModel().currentChanged.connect(self._on_current_changed)
        self.customContextMenuRequested.connect(self._on_menu)
        self.expanded.connect(lambda i: self._remember(i, True))
        self.collapsed.connect(lambda i: self._remember(i, False))
        model.rowsInserted.connect(self._on_rows_inserted)

    def _configure(self) -> None:
        self.setHeaderHidden(True)
        self.setUniformRowHeights(True)
        self.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)

    # --- search -------------------------------------------------------------
    def set_query(self, text: str) -> None:
        """Filter the tree; matches are expanded, and expansion is restored when cleared."""
        self._proxy.set_query(text)
        if self._proxy.active:
            self.expandAll()
        else:
            self.restore_expansion()

    # --- helpers for the controller ----------------------------------------
    def item_at(self, index: QModelIndex) -> LibraryItem | None:
        """The LibraryItem behind a proxy index, or None."""
        return self._model.library_item(self._proxy.mapToSource(index))

    def selected_items(self) -> list[LibraryItem]:
        """Items of all selected rows."""
        items = [self.item_at(i) for i in self.selectionModel().selectedIndexes() if i.column() == 0]
        return [i for i in items if i is not None]

    def restore_expansion(self) -> None:
        """Re-expand every row whose path the user previously expanded."""
        for index in _walk(self._proxy, QModelIndex()):
            item = self.item_at(index)
            if item is not None and item.path in self._expanded:
                self.setExpanded(index, True)

    def expand_path(self, path: Path) -> None:
        """Remember `path` as expanded (applied by `restore_expansion`)."""
        self._expanded.add(path)

    def collapse_everything(self) -> None:
        """Collapse all rows and forget the expansion memory."""
        self.collapseAll()
        self._expanded.clear()

    # --- slots --------------------------------------------------------------
    def _on_current_changed(self, current: QModelIndex, _previous: QModelIndex) -> None:
        item = self.item_at(current)
        if item is not None and item.opens_entry:
            self.item_chosen.emit(item)

    def _on_menu(self, pos: QPoint) -> None:
        self.menu_requested.emit(self.item_at(self.indexAt(pos)), self.viewport().mapToGlobal(pos))

    def _on_rows_inserted(self, parent: QModelIndex, first: int, last: int) -> None:
        if not parent.isValid():  # a (re)scanned root: open it the first time, then restore memory
            for row in range(first, last + 1):
                item = self._model.library_item(self._model.index(row, 0))
                if item is not None and item.path not in self._seen_roots:
                    self._seen_roots.add(item.path)
                    self._expanded.add(item.path)
        QTimer.singleShot(0, self.restore_expansion)

    def _remember(self, index: QModelIndex, expanded: bool) -> None:
        item = self.item_at(index)
        if item is None or self._proxy.active:
            return
        (self._expanded.add if expanded else self._expanded.discard)(item.path)


def _walk(model, parent: QModelIndex):
    for row in range(model.rowCount(parent)):
        index = model.index(row, 0, parent)
        yield index
        yield from _walk(model, index)
