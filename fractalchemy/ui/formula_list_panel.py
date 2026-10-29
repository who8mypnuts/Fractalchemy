"""The Formula Editor's list of every loaded formula, with a search box and the *New formula* button.

Rows come from the registry (built-ins, the bundled library and the user's own formulas — the latter in
bold), tagged like the Transform Editor's Variations list (`pre` / `post` / `3D` / `DC` / `random`) and with
where they came from. Clicking a row asks the window to load it (`formula_chosen`); the window decides
whether unsaved edits allow that.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QAbstractItemView, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from ..formulas import workbench as W
from ..fractal import variations as V
from .editor_value_tabs import variation_tags

SEARCH_DEBOUNCE_MS = 200
ORIGIN_BUILTIN, ORIGIN_LIBRARY, ORIGIN_USER = "built-in", "library", "user"


def short_origin(var: V.Variation) -> str:
    """`built-in` (native Python), `user` (the user's folders) or `library` (bundled sources)."""
    if var.style == V.LEGACY:
        return ORIGIN_BUILTIN
    path = W.origin_path(var)
    if path is not None and W.is_user_file(path):
        return ORIGIN_USER
    return ORIGIN_LIBRARY if "library" in (path.parts if path is not None else ()) else ORIGIN_USER


class FormulaListPanel(QWidget):
    """Search box, *New formula* button and the formula tree.

    Signals:
        formula_chosen(str): A row was clicked / activated.
        new_requested(): The *New formula* button.
    """
    formula_chosen = Signal(str)
    new_requested = Signal()

    def __init__(self, parent: QWidget | None = None, user_dir=None):
        """Args:
            parent: Qt owner.
            user_dir: Folder whose formulas count as the user's (the per-user folder by default).
        """
        super().__init__(parent)
        self.user_dir = user_dir
        self.search = QLineEdit(self, placeholderText="Search formulas…")
        self.search.setClearButtonEnabled(True)
        self.new_button = QPushButton("New formula", self)
        self.new_button.setToolTip("Start a new formula from the boilerplate template")
        self.tree = QTreeWidget(self)
        self.tree.setHeaderLabels(["Formula", "Tags", "Origin"])
        self.tree.setRootIsDecorated(False)
        self.tree.setUniformRowHeights(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setColumnWidth(0, 170)
        self.tree.setColumnWidth(1, 60)
        self.tree.setToolTip("Every loaded formula; click one to load its code (your own formulas in bold)")
        self.count_label = QLabel(self)
        self.count_label.setEnabled(False)
        top = QHBoxLayout()
        top.addWidget(self.search, 1)
        top.addWidget(self.new_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top)
        layout.addWidget(self.tree, 1)
        layout.addWidget(self.count_label)
        self._search_timer = QTimer(self, singleShot=True, interval=SEARCH_DEBOUNCE_MS)
        self._search_timer.timeout.connect(self.apply_filter)
        self.search.textChanged.connect(lambda _t: self._search_timer.start())
        self.search.returnPressed.connect(self._choose_first_visible)
        self.tree.itemClicked.connect(lambda item, _c: self._choose(item))
        self.tree.itemActivated.connect(lambda item, _c: self._choose(item))
        self.new_button.clicked.connect(self.new_requested)
        self.populate()

    # --- contents ------------------------------------------------------------------------------------------
    def populate(self) -> None:
        """(Re)list every formula of the catalogue, keeping the filter."""
        current = self.current_name()
        self.tree.clear()
        bold = QFont(self.tree.font())
        bold.setBold(True)
        for name in V.catalogue():
            var = V.REGISTRY[name]
            origin = short_origin(var) if self.user_dir is None else self._origin_with_user_dir(var)
            item = QTreeWidgetItem([name, variation_tags(var), origin])
            item.setData(0, Qt.ItemDataRole.UserRole, name)
            item.setToolTip(0, var.summary() + (f"\n{var.origin}" if var.origin else ""))
            if origin == ORIGIN_USER:
                item.setFont(0, bold)
            self.tree.addTopLevelItem(item)
        self.apply_filter()
        if current:
            self.select(current)

    def _origin_with_user_dir(self, var: V.Variation) -> str:
        path = W.origin_path(var)
        if path is not None and path.parent == self.user_dir:
            return ORIGIN_USER
        return short_origin(var)

    def apply_filter(self) -> None:
        """Hide the rows that do not contain the search text (name or tags)."""
        needle = self.search.text().strip().lower()
        shown = 0
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            hit = not needle or needle in item.text(0).lower() or needle in item.text(1).lower() or needle in item.text(2).lower()
            item.setHidden(not hit)
            shown += hit
        total = self.tree.topLevelItemCount()
        self.count_label.setText(f"{shown} of {total} formulas" if needle else f"{total} formulas")

    def visible_names(self) -> list[str]:
        """The names currently listed (after the filter)."""
        return [self.tree.topLevelItem(i).text(0) for i in range(self.tree.topLevelItemCount()) if not self.tree.topLevelItem(i).isHidden()]

    def current_name(self) -> str | None:
        """The selected formula's name, if any."""
        item = self.tree.currentItem()
        return item.data(0, Qt.ItemDataRole.UserRole) if item is not None else None

    def select(self, name: str | None) -> None:
        """Highlight `name` in the list without announcing it (None clears the highlight)."""
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item.data(0, Qt.ItemDataRole.UserRole) == name:
                self.tree.setCurrentItem(item)
                self.tree.scrollToItem(item)
                return
        self.tree.setCurrentItem(None)

    # --- choosing ------------------------------------------------------------------------------------------
    def _choose(self, item: QTreeWidgetItem | None) -> None:
        if item is not None:
            self.formula_chosen.emit(item.data(0, Qt.ItemDataRole.UserRole))

    def _choose_first_visible(self) -> None:
        names = self.visible_names()
        if names:
            self.select(names[0])
            self.formula_chosen.emit(names[0])


__all__ = ["FormulaListPanel", "short_origin"]
