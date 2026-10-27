"""A horizontal QSplitter whose outer panes hide/show via centred arrows on their handles.

Two panes: the first pane collapses (the Gradient Library). Three panes: the first
*and* the last pane collapse independently (the main window's library and settings
panels); the middle pane takes all resizing. With `collapse_last=True` a two-pane
splitter collapses its *last* pane instead (the Script Editor's drawer on the right).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QSplitter, QSplitterHandle, QStyle, QToolButton, QVBoxLayout, QWidget

DEFAULT_FIRST_WIDTH = 260
DEFAULT_LAST_WIDTH = 260


class CollapseHandle(QSplitterHandle):
    """Splitter handle with a centred arrow button.

    Signals:
        clicked(): The arrow was clicked.
    """
    clicked = Signal()

    def __init__(self, orientation, parent: "CollapsibleSplitter"):
        """Build the arrow button centred in the handle."""
        super().__init__(orientation, parent)
        self.button = QToolButton(self)
        self.button.setAutoRaise(True)
        self.button.setFixedSize(12, 48)
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.button.clicked.connect(self.clicked)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch(1)
        layout.addWidget(self.button, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)

    def set_state(self, collapsed: bool, pane_on_left: bool, label: str) -> None:
        """Point the arrow towards the pane it hides (or away, to restore it) and set the tooltip."""
        hide_arrow = QStyle.StandardPixmap.SP_ArrowLeft if pane_on_left else QStyle.StandardPixmap.SP_ArrowRight
        show_arrow = QStyle.StandardPixmap.SP_ArrowRight if pane_on_left else QStyle.StandardPixmap.SP_ArrowLeft
        self.button.setIcon(self.style().standardIcon(show_arrow if collapsed else hide_arrow))
        self.button.setToolTip(f"Show {label}" if collapsed else f"Hide {label}")

    def set_collapsed(self, collapsed: bool) -> None:
        """Two-pane behaviour: the handle controls the pane on its left."""
        self.set_state(collapsed, True, "library")


class CollapsibleSplitter(QSplitter):
    """Horizontal splitter whose first (and, with three panes, last) pane can be hidden via the handle arrows.

    Signals:
        collapsed_changed(bool): The first pane was collapsed (True) or restored.
        last_collapsed_changed(bool): The last pane was collapsed (True) or restored (three panes only).
    """
    collapsed_changed = Signal(bool)
    last_collapsed_changed = Signal(bool)

    def __init__(self, parent: QWidget | None = None, first_width: int = DEFAULT_FIRST_WIDTH,
                 last_width: int = DEFAULT_LAST_WIDTH, collapse_last: bool = False):
        """Create an empty horizontal splitter; add two or three widgets.

        Args:
            first_width: Width the first pane opens at.
            last_width: Width the last pane opens at (three panes, or `collapse_last`).
            collapse_last: With two panes, make the *last* pane the collapsible one (a drawer on the right).
        """
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._last_width = first_width
        self._last_pane_width = last_width
        self._collapse_last = collapse_last
        self._initialised = False
        self.first_label = "library"
        self.last_label = "panel"
        self.setHandleWidth(14)
        self.setChildrenCollapsible(True)
        self.splitterMoved.connect(lambda *_: self._sync())

    def createHandle(self) -> QSplitterHandle:
        handle = CollapseHandle(self.orientation(), self)
        handle.clicked.connect(lambda h=handle: self._on_handle_clicked(h))
        return handle

    # --- first pane -----------------------------------------------------------
    def set_first_width(self, width: int) -> None:
        """Width the first pane opens at (applied on show, or immediately if already expanded)."""
        self._last_width = max(1, width)
        if self._initialised and not self.is_collapsed():
            self._apply_sizes(first=self._last_width)

    def _first_collapsible(self) -> bool:
        return not (self._collapse_last and self.count() == 2)

    def is_collapsed(self) -> bool:
        """True when the first pane has zero width (never with a two-pane `collapse_last` splitter)."""
        sizes = self.sizes()
        return self._first_collapsible() and bool(sizes) and sizes[0] == 0

    def set_collapsed(self, collapsed: bool) -> None:
        """Collapse the first pane to zero width, or restore its last width."""
        if not self._first_collapsible() or collapsed == self.is_collapsed():
            return
        if collapsed:
            self._last_width = self.sizes()[0] or self._last_width
        self._apply_sizes(first=0 if collapsed else self._last_width)
        self._sync()

    def toggle(self) -> None:
        """Collapse if expanded, expand if collapsed."""
        self.set_collapsed(not self.is_collapsed())

    # --- last pane (three-pane layouts) -----------------------------------------
    def has_last_pane(self) -> bool:
        """True if the last pane collapses on its own: three panes, or two with `collapse_last`."""
        return self.count() >= 3 or (self._collapse_last and self.count() == 2)

    def set_last_width(self, width: int) -> None:
        self._last_pane_width = max(1, width)
        if self._initialised and self.has_last_pane() and not self.is_last_collapsed():
            self._apply_sizes(last=self._last_pane_width)

    def is_last_collapsed(self) -> bool:
        """True when the last pane has zero width (always False with two panes)."""
        sizes = self.sizes()
        return self.has_last_pane() and sizes[-1] == 0

    def set_last_collapsed(self, collapsed: bool) -> None:
        if not self.has_last_pane() or collapsed == self.is_last_collapsed():
            return
        if collapsed:
            self._last_pane_width = self.sizes()[-1] or self._last_pane_width
        self._apply_sizes(last=0 if collapsed else self._last_pane_width)
        self._sync()

    def toggle_last(self) -> None:
        self.set_last_collapsed(not self.is_last_collapsed())

    # --- internals -------------------------------------------------------------
    def _on_handle_clicked(self, handle: QSplitterHandle) -> None:
        index = next((i for i in range(1, self.count()) if self.handle(i) is handle), None)
        if index is None:
            return
        if self.has_last_pane() and index == self.count() - 1:
            self.toggle_last()
        elif index == 1:
            self.toggle()

    def _apply_sizes(self, first: int | None = None, last: int | None = None) -> None:
        sizes = self.sizes()
        total = sum(sizes) or self.width()
        if self.has_last_pane() and last is None:
            last = 0 if self.is_last_collapsed() else (sizes[-1] if sizes else self._last_pane_width)
        if not self._first_collapsible():
            self.setSizes([max(1, total - last), last])
            return
        if first is None:
            first = 0 if self.is_collapsed() else (sizes[0] if sizes else self._last_width)
        if self.has_last_pane():
            self.setSizes([first, max(1, total - first - last), last])
        else:
            self.setSizes([first, max(1, total - first)])

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._initialised and self.count() >= 2:
            self._initialised = True
            self._apply_sizes(first=self._last_width, last=self._last_pane_width if self.has_last_pane() else None)
        self._sync()

    def _sync(self) -> None:
        sizes = self.sizes()
        collapsed = self.is_collapsed()
        if self._first_collapsible():
            if not collapsed and sizes:
                self._last_width = sizes[0]  # remember the user's chosen width
            if self.count() >= 2:
                self.handle(1).set_state(collapsed, True, self.first_label)
            self.collapsed_changed.emit(collapsed)
        if self.has_last_pane():
            last_collapsed = self.is_last_collapsed()
            if not last_collapsed:
                self._last_pane_width = sizes[-1]
            self.handle(self.count() - 1).set_state(last_collapsed, False, self.last_label)
            self.last_collapsed_changed.emit(last_collapsed)
