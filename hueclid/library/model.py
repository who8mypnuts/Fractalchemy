"""Tree model of library roots → folders → files → gradient entries.

Built from ScannedDir results; never touches the disk itself. Drag/drop and
paste are turned into `drop_requested` signals for the controller to act on.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QModelIndex, Qt, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QApplication, QStyle

from .items import Kind, LibraryItem
from .payload import MIME_TYPE, from_mime, to_mime
from .scanner import ScannedDir, ScannedFile

ITEM_ROLE = Qt.ItemDataRole.UserRole + 1     # LibraryItem
SEARCH_ROLE = Qt.ItemDataRole.UserRole + 2   # text the search box matches against
COUNT_ROLE = Qt.ItemDataRole.UserRole + 3    # supported files under a root


class LibraryModel(QStandardItemModel):
    drop_requested = Signal(list, object, bool)  # items, target LibraryItem, move?

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHorizontalHeaderLabels(["Library"])
        self._icons = _Icons()

    # --- population ---------------------------------------------------------
    def root_paths(self) -> list[Path]:
        return [self.item(row).data(ITEM_ROLE).path for row in range(self.rowCount())]

    def set_root(self, scanned: ScannedDir) -> QStandardItem:
        """Insert or replace the subtree for one library root."""
        item = self._build_dir(scanned, Kind.ROOT)
        item.setData(scanned.file_count(), COUNT_ROLE)
        item.setToolTip(str(scanned.path))
        row = self._row_of_root(scanned.path)
        if row is None:
            self.appendRow(item)
        else:
            self.removeRow(row)
            self.insertRow(row, item)
        return item

    def remove_root(self, path: Path) -> None:
        row = self._row_of_root(path)
        if row is not None:
            self.removeRow(row)

    def file_counts(self) -> dict[Path, int]:
        return {self.item(r).data(ITEM_ROLE).path: self.item(r).data(COUNT_ROLE) for r in range(self.rowCount())}

    def library_item(self, index: QModelIndex) -> LibraryItem | None:
        return index.data(ITEM_ROLE) if index.isValid() else None

    def index_for(self, target: LibraryItem) -> QModelIndex:
        for item in self._walk(self.invisibleRootItem()):
            data = item.data(ITEM_ROLE)
            if data.path == target.path and data.kind == target.kind and data.index == target.index:
                return item.index()
        return QModelIndex()

    # --- drag & drop --------------------------------------------------------
    def supportedDropActions(self):
        return Qt.DropAction.MoveAction | Qt.DropAction.CopyAction

    def mimeTypes(self):
        return [MIME_TYPE, "text/uri-list"]

    def mimeData(self, indexes):
        return to_mime([self.library_item(i) for i in indexes if i.column() == 0])

    def canDropMimeData(self, data, action, row, column, parent):
        target = self.library_item(parent)
        items = from_mime(data)
        return bool(items) and target is not None and all(_droppable(i, target) for i in items)

    def dropMimeData(self, data, action, row, column, parent):
        if not self.canDropMimeData(data, action, row, column, parent):
            return False
        self.drop_requested.emit(from_mime(data), self.library_item(parent), action == Qt.DropAction.MoveAction)
        return False  # we rebuild from disk after the operation; don't let the view edit rows

    # --- building -----------------------------------------------------------
    def _build_dir(self, scanned: ScannedDir, kind: Kind) -> QStandardItem:
        item = self._make_item(LibraryItem(kind, scanned.path, name=scanned.path.name), self._icons.folder)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDropEnabled)
        for sub in scanned.dirs:
            item.appendRow(self._build_dir(sub, Kind.DIR))
        for file in scanned.files:
            item.appendRow(self._build_file(file))
        return item

    def _build_file(self, scanned: ScannedFile) -> QStandardItem:
        item = self._make_item(LibraryItem(Kind.FILE, scanned.path, name=scanned.path.name), self._icons.file)
        item.setData(" ".join([scanned.path.name, *scanned.names]), SEARCH_ROLE)
        item.setToolTip(str(scanned.path))
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled
        if _accepts_entries(scanned.path):
            flags |= Qt.ItemFlag.ItemIsDropEnabled
        item.setFlags(flags)
        if scanned.multi:
            for i, name in enumerate(scanned.names):
                item.appendRow(self._build_entry(scanned.path, i, name))
        return item

    def _build_entry(self, path: Path, index: int, name: str) -> QStandardItem:
        item = self._make_item(LibraryItem(Kind.GRADIENT, path, index, name), self._icons.gradient)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled)
        return item

    def _make_item(self, data: LibraryItem, icon) -> QStandardItem:
        item = QStandardItem(icon, data.name)
        item.setEditable(False)
        item.setData(data, ITEM_ROLE)
        item.setData(data.name, SEARCH_ROLE)
        return item

    def _row_of_root(self, path: Path) -> int | None:
        for row in range(self.rowCount()):
            if self.item(row).data(ITEM_ROLE).path == path:
                return row
        return None

    def _walk(self, item: QStandardItem):
        for row in range(item.rowCount()):
            child = item.child(row)
            yield child
            yield from self._walk(child)


def _accepts_entries(path: Path) -> bool:
    from ..formats import format_for  # local import keeps model import light

    return format_for(path).can_append


def _droppable(item: LibraryItem, target: LibraryItem) -> bool:
    if item.kind == Kind.GRADIENT:
        return target.is_directory or (target.kind == Kind.FILE and target.path != item.path)
    if item.kind == Kind.FILE:
        return target.is_directory or (target.kind == Kind.FILE and target.path != item.path)
    return False


class _Icons:
    def __init__(self):
        style = QApplication.style()
        self.folder = style.standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        self.file = style.standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        self.gradient = style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
