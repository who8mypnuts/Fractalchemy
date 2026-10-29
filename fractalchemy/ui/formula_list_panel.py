"""The Formula Editor's list of every loaded formula: search, origin / kind filters, favourites, the *New formula* button.

Rows come from the registry — built-ins, the Apophysis plugin library, the JWildfire translations and the
user's own formulas, each origin on its own light background (`formula_origins`) with the user's in bold —
tagged like the Transform Editor's Variations list (`pre` / `post` / `3D` / `DC` / `random`), with where
they came from and, when the source file names one, the author. Columns sort on click. Clicking a row
asks the window to load it (`formula_chosen`); the window decides whether unsaved edits allow that. A
double-click on the star column (or the context menu) marks a favourite; the set is the window's to persist.
"""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QFont
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QHBoxLayout, QLabel, QLineEdit, QMenu, QPushButton, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

from ..formulas import workbench as W
from ..fractal import variations as V
from .editor_value_tabs import variation_tags
from .formula_origins import ORDER, ORIGINS, USER, origin_of

SEARCH_DEBOUNCE_MS = 200
ORIGIN_FILTERS = ("All", "Favourites") + tuple(ORIGINS[key].label for key in ORDER)
KIND_FILTERS = ("Any kind", "normal", "pre", "post", "3D", "DC", "random")
STAR, NO_STAR = "★", "☆"
COLUMN_STAR, COLUMN_NAME, COLUMN_TAGS, COLUMN_ORIGIN, COLUMN_AUTHOR = range(5)
_AUTHOR_PATTERNS = (
    re.compile(r"Copyright\s*(?:\([cC]\)|©)?\s*[\d\-–,\s]*(?:by\s+)?([A-Z][A-Za-z.'\-]+(?: [A-Z][A-Za-z.'\-]+){0,3})"),
    re.compile(r"(?:Author|Written by|Ported by hand from [^\n(]*\([^\n,]*,)\s*:?\s*([A-Z][A-Za-z.'\-]+(?: [A-Z][A-Za-z.'\-]+){0,3})"),
)
_authors: dict[Path, str] = {}


def short_origin(var: V.Variation, user_dir: Path | None = None) -> str:
    """The origin key shown in the list: `built-in`, `apophysis`, `jwildfire` or `user` (see `formula_origins`)."""
    return origin_of(var, user_dir)


def author_of(var: V.Variation) -> str:
    """The author a formula file's header names (`Copyright (C) 2009 Michael Faber`, `Author: …`), or "" (cached per file)."""
    path = W.origin_path(var)
    if path is None:
        return ""
    if path not in _authors:
        author = ""
        try:
            head = path.read_text(encoding="utf-8", errors="replace")[:3000]
        except OSError:
            head = ""
        by_line = re.search(r"\n\s+by ([A-Z][A-Za-z.'\- ]{2,40})\s*\n", head[:600])     # a translated file's credit line
        if by_line:
            author = by_line.group(1).strip()
        elif "translated from the JWildfire" not in head:          # (JWildfire's own copyright line names the project, not the variation)
            for pattern in _AUTHOR_PATTERNS:
                m = pattern.search(head)
                if m and not m.group(1).startswith(("Fractalchemy", "Apophysis", "Free Software", "All", "GPL")):
                    author = re.sub(r"\s+", " ", m.group(1)).strip(" -.")
                    break
        _authors[path] = author
    return _authors[path]


class FormulaListPanel(QWidget):
    """Search box, filters, *New formula* button and the formula tree.

    Signals:
        formula_chosen(str): A row was clicked / activated.
        new_requested(): The *New formula* button.
        favourites_changed(): A star was toggled.
    """
    formula_chosen = Signal(str)
    new_requested = Signal()
    favourites_changed = Signal()

    def __init__(self, parent: QWidget | None = None, user_dir: Path | None = None):
        """Args:
            parent: Qt owner.
            user_dir: Folder whose formulas count as the user's (the per-user folder by default).
        """
        super().__init__(parent)
        self.user_dir = user_dir
        self.favourites: set[str] = set()
        self.search = QLineEdit(self, placeholderText="Search formulas…")
        self.search.setClearButtonEnabled(True)
        self.new_button = QPushButton("New formula", self)
        self.new_button.setToolTip("Start a new formula from a template")
        self.origin_filter = QComboBox(self)
        self.origin_filter.addItems(ORIGIN_FILTERS)
        self.origin_filter.setToolTip("Show every formula, only your favourites, or one origin (the row colours: "
                                      + "; ".join(f"{o.label} = {o.description}" for o in ORIGINS.values()) + ")")
        self.kind_filter = QComboBox(self)
        self.kind_filter.addItems(KIND_FILTERS)
        self.kind_filter.setToolTip("Show only pre / post / 3D / direct-colour / random formulas")
        self.tree = QTreeWidget(self)
        self.tree.setHeaderLabels(["", "Formula", "Tags", "Origin", "Author"])
        self.tree.setRootIsDecorated(False)
        self.tree.setUniformRowHeights(True)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setColumnWidth(COLUMN_STAR, 22)
        self.tree.setColumnWidth(COLUMN_NAME, 150)
        self.tree.setColumnWidth(COLUMN_TAGS, 60)
        self.tree.setColumnWidth(COLUMN_ORIGIN, 56)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.setToolTip("Every loaded formula; click one to load its code (your own formulas in bold). "
                             "Click a heading to sort; double-click the star to keep a favourite.")
        self.count_label = QLabel(self)
        self.count_label.setEnabled(False)
        top = QHBoxLayout()
        top.addWidget(self.search, 1)
        top.addWidget(self.new_button)
        filters = QHBoxLayout()
        filters.addWidget(self.origin_filter, 1)
        filters.addWidget(self.kind_filter, 1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top)
        layout.addLayout(filters)
        layout.addWidget(self.tree, 1)
        layout.addWidget(self.count_label)
        self._search_timer = QTimer(self, singleShot=True, interval=SEARCH_DEBOUNCE_MS)
        self._search_timer.timeout.connect(self.apply_filter)
        self.search.textChanged.connect(lambda _t: self._search_timer.start())
        self.search.returnPressed.connect(self._choose_first_visible)
        self.origin_filter.currentIndexChanged.connect(lambda _i: self.apply_filter())
        self.kind_filter.currentIndexChanged.connect(lambda _i: self.apply_filter())
        self.tree.itemClicked.connect(self._clicked)
        self.tree.itemActivated.connect(lambda item, _c: self._choose(item))
        self.tree.itemDoubleClicked.connect(self._double_clicked)
        self.tree.customContextMenuRequested.connect(self._context_menu)
        self.new_button.clicked.connect(self.new_requested)
        self.populate()

    # --- contents ------------------------------------------------------------------------------------------
    def populate(self) -> None:
        """(Re)list every formula of the catalogue, keeping the filter and the selection."""
        current = self.current_name()
        self.tree.clear()
        bold = QFont(self.tree.font())
        bold.setBold(True)
        self.tree.setSortingEnabled(False)
        for name in V.catalogue():
            var = V.REGISTRY[name]
            origin = ORIGINS[short_origin(var, self.user_dir)]
            item = QTreeWidgetItem([STAR if name in self.favourites else NO_STAR, name, variation_tags(var), origin.label, author_of(var)])
            item.setData(COLUMN_NAME, Qt.ItemDataRole.UserRole, name)
            item.setTextAlignment(COLUMN_STAR, Qt.AlignmentFlag.AlignCenter)
            item.setToolTip(COLUMN_NAME, var.summary() + (f"\n{var.origin}" if var.origin else ""))
            item.setToolTip(COLUMN_ORIGIN, origin.description)
            for column in range(COLUMN_AUTHOR + 1):
                item.setBackground(column, QBrush(origin.background_color))
                item.setForeground(column, QBrush(origin.text_color))
            if origin.key == USER:
                item.setFont(COLUMN_NAME, bold)
            self.tree.addTopLevelItem(item)
        self.tree.setSortingEnabled(True)
        self.tree.sortItems(COLUMN_NAME, Qt.SortOrder.AscendingOrder)
        self.apply_filter()
        if current:
            self.select(current)

    def apply_filter(self) -> None:
        """Hide the rows the search text and the origin / kind filters exclude; show the count."""
        needle = self.search.text().strip().lower()
        origin = self.origin_filter.currentText()
        kind = self.kind_filter.currentText()
        shown = 0
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            name, tags, where, author = (item.text(c) for c in (COLUMN_NAME, COLUMN_TAGS, COLUMN_ORIGIN, COLUMN_AUTHOR))
            hit = not needle or any(needle in field.lower() for field in (name, tags, where, author))
            if origin == "Favourites":
                hit = hit and name in self.favourites
            elif origin != "All":
                hit = hit and where == origin
            if kind == "normal":
                hit = hit and "pre" not in tags.split() and "post" not in tags.split()
            elif kind != "Any kind":
                hit = hit and kind in tags.split()
            item.setHidden(not hit)
            shown += hit
        total = self.tree.topLevelItemCount()
        self.count_label.setText(f"{shown} of {total} formulas" if shown != total else f"{total} formulas")

    def visible_names(self) -> list[str]:
        """The names currently listed (after the filters)."""
        return [self.tree.topLevelItem(i).text(COLUMN_NAME) for i in range(self.tree.topLevelItemCount())
                if not self.tree.topLevelItem(i).isHidden()]

    def current_name(self) -> str | None:
        """The selected formula's name, if any."""
        item = self.tree.currentItem()
        return item.data(COLUMN_NAME, Qt.ItemDataRole.UserRole) if item is not None else None

    def select(self, name: str | None) -> None:
        """Highlight `name` in the list without announcing it (None clears the highlight)."""
        item = self._item(name)
        self.tree.setCurrentItem(item)
        if item is not None:
            self.tree.scrollToItem(item)

    def _item(self, name: str | None) -> QTreeWidgetItem | None:
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item.data(COLUMN_NAME, Qt.ItemDataRole.UserRole) == name:
                return item
        return None

    # --- favourites ----------------------------------------------------------------------------------------
    def set_favourites(self, names) -> None:
        """Replace the favourite set (from the persisted list) and refresh the stars."""
        self.favourites = set(names)
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            item.setText(COLUMN_STAR, STAR if item.text(COLUMN_NAME) in self.favourites else NO_STAR)
        self.apply_filter()

    def toggle_favourite(self, name: str) -> bool:
        """Star or unstar `name`; returns whether it is a favourite now."""
        if name in self.favourites:
            self.favourites.discard(name)
        else:
            self.favourites.add(name)
        item = self._item(name)
        if item is not None:
            item.setText(COLUMN_STAR, STAR if name in self.favourites else NO_STAR)
        self.favourites_changed.emit()
        self.apply_filter()
        return name in self.favourites

    # --- choosing ------------------------------------------------------------------------------------------
    def _clicked(self, item: QTreeWidgetItem, column: int) -> None:
        if column != COLUMN_STAR:
            self._choose(item)

    def _double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        if column == COLUMN_STAR:
            self.toggle_favourite(item.text(COLUMN_NAME))

    def _choose(self, item: QTreeWidgetItem | None) -> None:
        if item is not None:
            self.formula_chosen.emit(item.data(COLUMN_NAME, Qt.ItemDataRole.UserRole))

    def _choose_first_visible(self) -> None:
        names = self.visible_names()
        if names:
            self.select(names[0])
            self.formula_chosen.emit(names[0])

    def _context_menu(self, pos: QPoint) -> None:
        item = self.tree.itemAt(pos)
        if item is None:
            return
        name = item.text(COLUMN_NAME)
        menu = QMenu(self)
        menu.addAction("Load", lambda: self._choose(item))
        menu.addAction("Remove from favourites" if name in self.favourites else "Add to favourites", lambda: self.toggle_favourite(name))
        menu.exec(self.tree.viewport().mapToGlobal(pos))


__all__ = ["FormulaListPanel", "short_origin", "author_of", "ORIGIN_FILTERS", "KIND_FILTERS"]
