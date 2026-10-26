"""Left-hand library pane: search box, tree, and the add / edit buttons."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QStyle, QToolButton, QVBoxLayout, QWidget

from .catalog import GRADIENT_CATALOG, Catalog
from .model import LibraryModel
from .tree import LibraryTree

SEARCH_DELAY_MS = 300


class LibraryPanel(QWidget):
    """Constructed empty (promotable in Designer); owns the model and tree, no disk access.

    Signals:
        add_requested(): The '+' button was clicked.
        edit_requested(): The edit button was clicked.
        item_chosen(LibraryItem): Relayed from the tree.
        menu_requested(LibraryItem | None, QPoint): Relayed from the tree.
    """

    add_requested = Signal()
    edit_requested = Signal()
    item_chosen = Signal(object)
    menu_requested = Signal(object, QPoint)

    def __init__(self, parent: QWidget | None = None, catalog: Catalog = GRADIENT_CATALOG):
        """Build the search box, tree and buttons for `catalog`; no disk access happens here."""
        super().__init__(parent)
        self.catalog = catalog
        self.model = LibraryModel(catalog, self)
        self.tree = LibraryTree(self.model, self)
        self.search = QLineEdit(self)
        self.collapse_button = QToolButton(self)
        self.add_button = QToolButton(self)
        self.edit_button = QToolButton(self)
        self._search_timer = QTimer(self, singleShot=True, interval=SEARCH_DELAY_MS)
        self._build()
        self._connect()

    def _build(self) -> None:
        self.search.setPlaceholderText("Search library…")
        self.search.setClearButtonEnabled(True)
        self.collapse_button.setIcon(_collapse_icon(self))
        self.collapse_button.setToolTip("Collapse All")
        self.collapse_button.setAutoRaise(True)
        top = QHBoxLayout()
        top.addWidget(self.search, 1)
        top.addWidget(self.collapse_button)
        self.add_button.setText("+")
        self.add_button.setToolTip(f"Add folder to the {self.catalog.title.lower()}")
        self.edit_button.setText("✎")
        self.edit_button.setToolTip(f"Edit {self.catalog.title.lower()}")
        buttons = QHBoxLayout()
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.edit_button)
        buttons.addStretch(1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 0, 4)
        layout.addLayout(top)
        layout.addWidget(self.tree, 1)
        layout.addLayout(buttons)
        self.setMinimumWidth(160)

    def _connect(self) -> None:
        self.search.textChanged.connect(lambda _: self._search_timer.start())
        self._search_timer.timeout.connect(lambda: self.tree.set_query(self.search.text()))
        self.collapse_button.clicked.connect(self.tree.collapse_everything)
        self.add_button.clicked.connect(self.add_requested)
        self.edit_button.clicked.connect(self.edit_requested)
        self.tree.item_chosen.connect(self.item_chosen)
        self.tree.menu_requested.connect(self.menu_requested)


def _collapse_icon(widget: QWidget) -> QIcon:
    """Theme icon where available (Breeze/Adwaita ship one), else Qt's 'shade' arrow."""
    fallback = widget.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarShadeButton)
    return QIcon.fromTheme("collapse-all", fallback)
