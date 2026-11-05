"""The fragment library's extras: tags, ratings, favourites, the *Show* filter, thumbnail sizes and captions.

`FragmentLibraryExtras` sits between the window's library pane and `fragments/library_meta.py`: after every rescan
it indexes the root's files on the thread pool and hands the model each row's search words and thumbnail caption;
its context menu (a `LibraryContextMenu` subclass) adds *Favourite*, *Rating* and *Tags…*; the panel's *Show* combo
narrows the tree to favourites, recent files, well-rated ones or a camera kind by appending a hidden search token;
the thumbnail size combo resizes the provider's renders.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, QSize
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QInputDialog, QMenu, QWidget

from ...formulas.loader import cache_dir
from ...fragments.examples import is_include
from ...fragments.library_meta import MAX_RATING, LibraryMeta
from ...library.context_menu import LibraryContextMenu
from ...library.items import LibraryItem
from ..background import run_in_background

SHOW_FILTERS = (("All fragments", ""), ("Favourites", "fav"), ("Recently opened", "recent"), ("Rated ★★★★ and up", "★★★★"),
                ("2D fragments", "2d"), ("3D fragments", "3d"))
THUMB_SIZES = (("Small", QSize(160, 100)), ("Medium", QSize(240, 150)), ("Large", QSize(320, 200)))
META_FILE = "library_meta.json"


class FragmentContextMenu(LibraryContextMenu):
    """The generic menu plus favourite / rating / tags for fragment files."""

    def __init__(self, controller, open_item, parent: QWidget, extras: "FragmentLibraryExtras"):
        super().__init__(controller, open_item, parent)
        self._extras = extras

    def _populate(self, menu: QMenu, item: LibraryItem, selection: list[LibraryItem]) -> None:
        super()._populate(menu, item, selection)
        if not item.opens_entry:
            return
        meta = self._extras.meta
        menu.addSeparator()
        favourite = menu.addAction("Favourite")
        favourite.setCheckable(True)
        favourite.setChecked(meta.favourite(item.path))
        favourite.toggled.connect(lambda on: self._extras.set_favourite(item, on))
        rating = menu.addMenu("Rating")
        current = meta.rating(item.path)
        for stars in range(MAX_RATING, -1, -1):
            action = rating.addAction("★" * stars if stars else "no rating")
            action.setCheckable(True)
            action.setChecked(stars == current)
            action.triggered.connect(lambda _c, n=stars: self._extras.set_rating(item, n))
        self._add(menu, "Tags…", lambda: self._extras.edit_tags(item))


class FragmentLibraryExtras(QObject):
    """Tags / ratings / favourites, indexing and the panel's extra controls (see the module docstring)."""

    def __init__(self, window, panel, controller, thumbnails, recent_provider: Callable[[], list[Path]], settings, store: Path | None = None):
        super().__init__(window)
        self.window = window
        self.panel = panel
        self.controller = controller
        self.thumbnails = thumbnails
        self.recent_provider = recent_provider
        self.settings = settings
        self.meta = LibraryMeta(store if store is not None else cache_dir() / "fragments" / META_FILE)
        self.menu = FragmentContextMenu(controller, window.open_item, window, self)
        self.show_combo = QComboBox(panel)
        for label, token in SHOW_FILTERS:
            self.show_combo.addItem(label, token)
        self.show_combo.setToolTip("Narrow the tree: favourites, recent files, ratings, camera kind (the search box adds to it)")
        self.size_combo = QComboBox(panel)
        for label, size in THUMB_SIZES:
            self.size_combo.addItem(label, size)
        self.size_combo.setToolTip("Thumbnail size")
        self._arrange_rows()
        self._connect()

    def _arrange_rows(self) -> None:
        """The search box keeps its row to itself; the filter, the thumbnail size and the view buttons go on a row below."""
        panel = self.panel
        top = panel.layout().itemAt(0).layout()
        for button in (panel.list_button, panel.thumb_button):
            top.removeWidget(button)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.show_combo, 1)
        row.addWidget(self.size_combo)
        row.addWidget(panel.list_button)
        row.addWidget(panel.thumb_button)
        panel.layout().insertLayout(1, row)

    def _connect(self) -> None:
        panel = self.panel
        panel._search_timer.timeout.disconnect()
        panel._search_timer.timeout.connect(self.apply_query)
        self.show_combo.currentIndexChanged.connect(lambda _i: self.apply_query())
        self.size_combo.currentIndexChanged.connect(lambda _i: self.apply_size())
        self.controller.root_scanned.connect(self.index_root)
        size = self.settings.value("fragments/thumb_size", "Small")
        self.size_combo.setCurrentIndex(max(0, self.size_combo.findText(str(size))))

    # --- queries --------------------------------------------------------------------------------------------------------
    def apply_query(self) -> None:
        token = str(self.show_combo.currentData() or "")
        self.panel.tree.set_query(f"{self.panel.search.text()} {token}".strip())

    def apply_size(self) -> None:
        size = self.size_combo.currentData()
        self.settings.setValue("fragments/thumb_size", self.size_combo.currentText())
        self.thumbnails.set_size(size)
        if self.panel.thumbnails_shown:
            self.panel.apply_icon_size(size)

    # --- indexing -------------------------------------------------------------------------------------------------------------
    def index_root(self, root: Path) -> None:
        """After a rescan: the search words and captions of every fragment under `root` (scanned on the thread pool)."""
        items = [item for item in self.panel.model.entries() if _under(item.path, root)]
        recent = {p.resolve() for p in self.recent_provider()}
        run_in_background(self._index, items, recent, on_done=self._apply_index, on_error=lambda _exc: None)

    def _index(self, items: list[LibraryItem], recent: set[Path]) -> list[tuple[LibraryItem, str, str, str]]:
        out = []
        for item in items:
            try:
                resolved = item.path.resolve()
            except OSError:
                continue
            text = self.meta.search_text(item.path, resolved in recent)
            caption = self.meta.caption(item.path)
            tooltip = str(item.path) + ("\n(include file)" if is_include(item.path) else "") + "\n" + "\n".join(self.meta.info(item.path).info[:3])
            out.append((item, text, caption, tooltip))
        return out

    def _apply_index(self, rows: list[tuple[LibraryItem, str, str, str]]) -> None:
        model = self.panel.model
        for item, text, caption, tooltip in rows:
            model.set_search_text(item, text)
            model.set_caption(item, caption, tooltip)
        if self.panel.search.text().strip() or self.show_combo.currentData():
            self.apply_query()

    def refresh_item(self, item: LibraryItem) -> None:
        recent = {p.resolve() for p in self.recent_provider()}
        self._apply_index(self._index([item], recent))

    # --- edits ------------------------------------------------------------------------------------------------------------------
    def set_favourite(self, item: LibraryItem, on: bool) -> None:
        self.meta.set_favourite(item.path, on)
        self.refresh_item(item)
        self.window.message(f"{item.name}: {'added to' if on else 'removed from'} the favourites")

    def set_rating(self, item: LibraryItem, stars: int) -> None:
        self.meta.set_rating(item.path, stars)
        self.refresh_item(item)

    def edit_tags(self, item: LibraryItem) -> None:
        current = ", ".join(self.meta.tags(item.path))
        known = ", ".join(self.meta.all_tags())
        text, ok = QInputDialog.getText(self.window, "Tags", f"Tags for {item.name} (comma separated)" + (f"\nKnown tags: {known}" if known else ""),
                                        text=current)
        if ok:
            self.meta.set_tags(item.path, text.split(","))
            self.refresh_item(item)


def _under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False


__all__ = ["FragmentLibraryExtras", "FragmentContextMenu", "SHOW_FILTERS", "THUMB_SIZES"]
