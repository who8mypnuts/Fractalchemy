"""A two-pane QSplitter whose handle carries a centred arrow to hide/show the first pane."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QSplitter, QSplitterHandle, QStyle, QToolButton, QVBoxLayout, QWidget

DEFAULT_FIRST_WIDTH = 260


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

    def set_collapsed(self, collapsed: bool) -> None:
        """Point the arrow and tooltip according to the pane state."""
        arrow = QStyle.StandardPixmap.SP_ArrowRight if collapsed else QStyle.StandardPixmap.SP_ArrowLeft
        self.button.setIcon(self.style().standardIcon(arrow))
        self.button.setToolTip("Show library" if collapsed else "Hide library")


class CollapsibleSplitter(QSplitter):
    """Horizontal two-pane splitter whose first pane can be hidden via the handle arrow.

    Signals:
        collapsed_changed(bool): The first pane was collapsed (True) or restored.
    """
    collapsed_changed = Signal(bool)

    def __init__(self, parent: QWidget | None = None):
        """Create an empty horizontal splitter; add exactly two widgets."""
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._last_width = DEFAULT_FIRST_WIDTH
        self._initialised = False
        self.setHandleWidth(14)
        self.setChildrenCollapsible(True)
        self.splitterMoved.connect(lambda *_: self._sync())

    def createHandle(self) -> QSplitterHandle:
        handle = CollapseHandle(self.orientation(), self)
        handle.clicked.connect(self.toggle)
        return handle

    # --- state --------------------------------------------------------------
    def is_collapsed(self) -> bool:
        """True when the first pane has zero width."""
        sizes = self.sizes()
        return bool(sizes) and sizes[0] == 0

    def set_collapsed(self, collapsed: bool) -> None:
        """Collapse the first pane to zero width, or restore its last width."""
        if collapsed == self.is_collapsed():
            return
        sizes = self.sizes()
        total = sum(sizes) or self.width()
        if collapsed:
            self._last_width = sizes[0] or self._last_width
            self.setSizes([0, total])
        else:
            self.setSizes([self._last_width, max(1, total - self._last_width)])
        self._sync()

    def toggle(self) -> None:
        """Collapse if expanded, expand if collapsed."""
        self.set_collapsed(not self.is_collapsed())

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._initialised and self.count() >= 2:
            self._initialised = True
            self.setSizes([self._last_width, max(1, self.width() - self._last_width)])
        self._sync()

    def _sync(self) -> None:
        collapsed = self.is_collapsed()
        if not collapsed and self.sizes():
            self._last_width = self.sizes()[0]  # remember the user's chosen width
        if self.count() >= 2:
            self.handle(1).set_collapsed(collapsed)
        self.collapsed_changed.emit(collapsed)
