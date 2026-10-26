"""Tree model of library roots → folders → files → entries (gradients or flames).

Built from ScannedDir results; never touches the disk itself. Drag/drop and
paste are turned into `drop_requested` signals for the controller to act on.
An optional thumbnail provider supplies icons for entry rows lazily, as the
view asks for them.
"""

from __future__ import annotations

from pathlib import Path

from typing import Protocol

from PySide6.QtCore import QModelIndex, Qt, Signal
from PySide6.QtGui import QIcon, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QApplication, QStyle

from .catalog import Catalog
from .items import Kind, LibraryItem
from .payload import MIME_TYPE, from_mime, to_mime
from .scanner import ScannedDir, ScannedFile

ITEM_ROLE = Qt.ItemDataRole.UserRole + 1     # LibraryItem
SEARCH_ROLE = Qt.ItemDataRole.UserRole + 2   # text the search box matches against
COUNT_ROLE = Qt.ItemDataRole.UserRole + 3    # supported files under a root


class ThumbnailProvider(Protocol):
    """Supplies icons for entry rows; may start background work and call `model.set_thumbnail` later."""
    def icon_for(self, item: LibraryItem) -> QIcon | None: ...


class LibraryModel(QStandardItemModel):
    """Item model behind the library tree.

    Rows are (re)built per root from ScannedDir results. Drops are validated
    here but executed by the controller, which then rescans from disk.

    Signals:
        drop_requested(list[LibraryItem], LibraryItem, bool): Items dropped onto a
            target; the bool is True for a move.
    """
    drop_requested = Signal(list, object, bool)

    def __init__(self, catalog: Catalog, parent=None):
        """Create an empty model with one 'Library' column for `catalog`'s file types."""
        super().__init__(parent)
        self.catalog = catalog
        self.setHorizontalHeaderLabels([catalog.title])
        self._icons = _Icons()
        self._thumbnails: ThumbnailProvider | None = None
        self._by_key: dict[tuple, QStandardItem] = {}

    # --- thumbnails ---------------------------------------------------------
    def set_thumbnail_provider(self, provider: ThumbnailProvider | None) -> None:
        """Use `provider` for entry-row icons (None restores the plain icons)."""
        self._thumbnails = provider
        if self.rowCount():
            self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount() - 1, 0), [Qt.ItemDataRole.DecorationRole])

    def set_thumbnail(self, item: LibraryItem, icon: QIcon) -> None:
        """Show `icon` on the row for `item` (no-op if the row is gone)."""
        row = self._by_key.get(_key(item))
        if row is not None:
            row.setIcon(icon)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DecorationRole and self._thumbnails is not None:
            item = super().data(index, ITEM_ROLE)
            if item is not None and item.opens_entry and not _is_multi_file(self, index):
                icon = self._thumbnails.icon_for(item)
                if icon is not None:
                    return icon
            return self._icons.small(super().data(index, role))  # folders / container files stay small
        return super().data(index, role)

    # --- population ---------------------------------------------------------
    def root_paths(self) -> list[Path]:
        """Paths of the roots currently in the tree, top to bottom."""
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
        self._reindex()
        return item

    def remove_root(self, path: Path) -> None:
        """Drop the subtree for `path` if present."""
        row = self._row_of_root(path)
        if row is not None:
            self.removeRow(row)
            self._reindex()

    def file_counts(self) -> dict[Path, int]:
        """Supported-file count per root path."""
        return {self.item(r).data(ITEM_ROLE).path: self.item(r).data(COUNT_ROLE) for r in range(self.rowCount())}

    def library_item(self, index: QModelIndex) -> LibraryItem | None:
        """The LibraryItem stored on `index`, or None for an invalid index."""
        return index.data(ITEM_ROLE) if index.isValid() else None

    def index_for(self, target: LibraryItem) -> QModelIndex:
        """The model index whose item matches `target` (kind, path, index), or an invalid index."""
        item = self._by_key.get(_key(target))
        return item.index() if item is not None else QModelIndex()

    def entries(self) -> list[LibraryItem]:
        """Every file / entry item in the tree (for thumbnail pre-loading)."""
        return [i.data(ITEM_ROLE) for i in self._by_key.values() if i.data(ITEM_ROLE).opens_entry]

    # --- drag & drop --------------------------------------------------------
    def supportedDropActions(self):
        return Qt.DropAction.MoveAction | Qt.DropAction.CopyAction

    def mimeTypes(self):
        return [MIME_TYPE, "text/uri-list"]

    def mimeData(self, indexes):
        return to_mime([self.library_item(i) for i in indexes if i.column() == 0], self.catalog.key)

    def canDropMimeData(self, data, action, row, column, parent):
        target = self.library_item(parent)
        items = from_mime(data, self.catalog.key)
        return bool(items) and target is not None and all(_droppable(i, target) for i in items)

    def dropMimeData(self, data, action, row, column, parent):
        if not self.canDropMimeData(data, action, row, column, parent):
            return False
        self.drop_requested.emit(from_mime(data, self.catalog.key), self.library_item(parent), action == Qt.DropAction.MoveAction)
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
        if self._accepts_entries(scanned.path):
            flags |= Qt.ItemFlag.ItemIsDropEnabled
        item.setFlags(flags)
        if scanned.multi:
            for i, name in enumerate(scanned.names):
                item.appendRow(self._build_entry(scanned.path, i, name))
        return item

    def _build_entry(self, path: Path, index: int, name: str) -> QStandardItem:
        item = self._make_item(LibraryItem(Kind.ENTRY, path, index, name), self._icons.entry)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled)
        return item

    def _make_item(self, data: LibraryItem, icon) -> QStandardItem:
        item = QStandardItem(icon, data.name)
        item.setEditable(False)
        item.setData(data, ITEM_ROLE)
        item.setData(data.name, SEARCH_ROLE)
        return item

    def _accepts_entries(self, path: Path) -> bool:
        try:
            return bool(self.catalog.format_for(path).can_append)
        except Exception:  # noqa: BLE001 - unknown type: not a drop target
            return False

    def _reindex(self) -> None:
        self._by_key = {_key(item.data(ITEM_ROLE)): item for item in self._walk(self.invisibleRootItem())}

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


def _key(item: LibraryItem) -> tuple:
    return (item.kind, item.path, item.index)


def _is_multi_file(model: QStandardItemModel, index: QModelIndex) -> bool:
    """A FILE row that has entry children shows the generic icon; its children carry the thumbnails."""
    return model.hasChildren(index)


def _droppable(item: LibraryItem, target: LibraryItem) -> bool:
    if item.kind == Kind.ENTRY:
        return target.is_directory or (target.kind == Kind.FILE and target.path != item.path)
    if item.kind == Kind.FILE:
        return target.is_directory or (target.kind == Kind.FILE and target.path != item.path)
    return False


class _Icons:
    SMALL = 16

    def __init__(self):
        """Fetch the standard folder / file / entry icons from the current style."""
        style = QApplication.style()
        self.folder = style.standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        self.file = style.standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        self.entry = style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
        self._small: dict[int, QIcon] = {}

    def small(self, icon: QIcon | None) -> QIcon | None:
        """A fixed 16 px version of `icon` (QIcon never upscales a single pixmap, so large view icon sizes leave it small)."""
        if icon is None or icon.isNull():
            return icon
        key = icon.cacheKey()
        if key not in self._small:
            self._small[key] = QIcon(icon.pixmap(self.SMALL, self.SMALL))
        return self._small[key]
