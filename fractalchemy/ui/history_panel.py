"""The Inspector's *History* tab: every state Undo / Redo can reach, by name, and a click to jump to any of them.

The rows come from `FractalDocument.history()`: the state as loaded ("Opened candy.flame #3") at the top, the steps
made since below it with the time they were made, the current state in bold, the undone (redo) steps dimmed, and the
saved state marked with a disk. Clicking a row calls `jump_to` — one announcement however many steps it crosses. The
right-click menu copies a state's parameters or compares it with the current picture (`compare_requested`, which the
main window hands to the viewport's before / after view).
"""

from __future__ import annotations

import time

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QMenu, QVBoxLayout, QWidget

from ..fractal.formats import flame_to_text
from ..widgets.theming import on_theme_changed, theme_color
from .fractal_document import FractalDocument

POSITION_ROLE = Qt.ItemDataRole.UserRole + 1
SAVED_MARK = "💾 "
EMPTY_TEXT = "Open a fractal: its edits are listed here, and any of them can be returned to."


def _clock(stamp: float) -> str:
    return time.strftime("%H:%M:%S", time.localtime(stamp)) if stamp else ""


class HistoryPanel(QWidget):
    """The History tab (see the module docstring).

    Signals:
        compare_requested(object): A state's flame to show in the viewport's before / after view.
    """
    compare_requested = Signal(object)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._document: FractalDocument | None = None
        self.list = QListWidget(self)
        self.list.setAlternatingRowColors(True)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.setToolTip("Click a step to go back (or forward) to it; right-click for more")
        self.hint = QLabel(EMPTY_TEXT, self)
        self.hint.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.list, 1)
        layout.addWidget(self.hint)
        self._dirty = False
        self._timer = QTimer(self, singleShot=True, interval=0)      # a burst of edits (a slider drag) rebuilds once
        self._timer.timeout.connect(self.refresh)
        self.list.itemClicked.connect(self._clicked)
        self.list.customContextMenuRequested.connect(self._menu)
        on_theme_changed(self, lambda _theme: self._schedule())

    def bind(self, document: FractalDocument) -> None:
        """Follow `document`'s history."""
        self._document = document
        for signal in (document.undo_changed, document.modified_changed, document.edited):
            signal.connect(lambda *_args: self._schedule())
        self.refresh()

    def _schedule(self) -> None:
        """Rebuild soon — or, while the tab is hidden, when it is next shown."""
        if self.isVisible():
            self._timer.start()
        else:
            self._dirty = True

    def showEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().showEvent(event)
        if self._dirty:
            self.refresh()

    # --- rows ---------------------------------------------------------------------------------------------------------
    def refresh(self) -> None:
        """Rebuild the rows from the document's history."""
        self._dirty = False
        document = self._document
        entries = document.history() if document is not None else []
        current = document.history_position if document is not None else 0
        saved = document.saved_position if document is not None else None
        self.list.blockSignals(True)
        self.list.clear()
        dim = theme_color("dim_text")
        for entry in entries:
            mark = SAVED_MARK if entry.position == saved else ""
            item = QListWidgetItem(f"{mark}{entry.label}")
            item.setData(POSITION_ROLE, entry.position)
            item.setToolTip(f"{entry.label} — {_clock(entry.time)}" + (" (saved)" if mark else "")
                            + ("  ← the fractal now" if entry.position == current else ""))
            if entry.position == current:
                font = QFont(item.font())
                font.setBold(True)
                item.setFont(font)
            elif entry.position > current:
                item.setForeground(dim)
            self.list.addItem(item)
        if 0 <= current < self.list.count():
            self.list.setCurrentRow(current)
            self.list.scrollToItem(self.list.item(current))
        self.list.blockSignals(False)
        self.hint.setVisible(not entries)

    def labels(self) -> list[str]:
        """The rows' texts (tests)."""
        return [self.list.item(i).text() for i in range(self.list.count())]

    # --- actions --------------------------------------------------------------------------------------------------------
    def _clicked(self, item: QListWidgetItem) -> None:
        if self._document is not None:
            self._document.jump_to(int(item.data(POSITION_ROLE)))

    def _menu(self, pos) -> None:
        item = self.list.itemAt(pos)
        if item is None or self._document is None:
            return
        self.menu_for(int(item.data(POSITION_ROLE))).exec(self.list.viewport().mapToGlobal(pos))

    def menu_for(self, position: int) -> QMenu:
        """The right-click menu of the row at history `position`."""
        menu = QMenu(self)
        document = self._document
        menu.addAction("Go to this state", lambda: document.jump_to(position))
        menu.addAction("Compare with this state", lambda: self.compare_requested.emit(document.state_at(position)))
        menu.addAction("Copy parameters of this state",
                       lambda: QGuiApplication.clipboard().setText(flame_to_text(document.state_at(position))))
        return menu


__all__ = ["HistoryPanel"]
