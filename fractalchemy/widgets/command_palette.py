"""The command palette (`Ctrl+K`): type a few letters of anything a window can do and press Enter.

`CommandPalette` is a popup near the top of the window it serves: a query line and a list of `Command`s (title, where
it lives — "Edit ▸ Copy Parameters As" —, its shortcut, whether it is available). Matching is fuzzy (`search.fuzzy_score`:
letters in order, word starts and runs count most); with an empty query the commands used last come first. ↑ / ↓ move,
Enter runs, Esc closes; unavailable commands are listed dimmed and do not run. The palette only shows and runs
commands: the caller (`ui/commands.py`) decides what they are.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QLineEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from ..search import fuzzy_score
from .theming import theme_color

MAX_SHOWN = 60
RECENT_FIRST = 5
WIDTH = 620


@dataclass
class Command:
    """One thing the palette can run."""
    title: str
    path: str = ""
    shortcut: str = ""
    run: Callable[[], None] | None = None
    enabled: bool = True
    icon: QIcon | None = None

    @property
    def key(self) -> str:
        return f"{self.path} ▸ {self.title}" if self.path else self.title


def rank(commands: list[Command], query: str, recent: list[str] = ()) -> list[Command]:
    """The commands matching `query`, best first (the recently used first when the query is empty)."""
    if not query.strip():
        order = {key: i for i, key in enumerate(recent[:RECENT_FIRST])}
        return sorted(commands, key=lambda c: (order.get(c.key, RECENT_FIRST), not c.enabled, c.path, c.title))
    scored = []
    for i, command in enumerate(commands):
        title = fuzzy_score(query, command.title)
        where = fuzzy_score(query, command.key)
        candidates = [s for s in (title * 2 if title is not None else None, where) if s is not None]   # the title counts double
        if candidates:
            scored.append((max(candidates) - (0 if command.enabled else 5), i, command))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [command for _score, _i, command in scored]


class CommandPalette(QDialog):
    """The popup (see the module docstring).

    Signals:
        ran(str): A command ran (its `key`).
    """
    ran = Signal(str)

    def __init__(self, commands: list[Command], recent: list[str] = (), parent: QWidget | None = None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.commands = list(commands)
        self.recent = list(recent)
        self.query = QLineEdit(self)
        self.query.setPlaceholderText("Type a command… (↑ ↓ to choose, Enter to run, Esc to close)")
        self.list = QTreeWidget(self)
        self.list.setColumnCount(3)
        self.list.setHeaderHidden(True)
        self.list.setRootIsDecorated(False)
        self.list.setUniformRowHeights(True)
        self.list.setColumnWidth(0, 280)
        self.list.setColumnWidth(1, 230)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.query)
        layout.addWidget(self.list, 1)
        self.resize(WIDTH, 380)
        self.query.textChanged.connect(self.refresh)
        self.query.installEventFilter(self)
        self.list.itemActivated.connect(lambda _item, _col: self.run_current())
        self.refresh("")
        if parent is not None:
            top = parent.mapToGlobal(parent.rect().topLeft())
            self.move(top.x() + (parent.width() - WIDTH) // 2, top.y() + 60)

    def refresh(self, query: str) -> None:
        """Show the commands matching `query`."""
        self.list.clear()
        dim = theme_color("dim_text")
        for command in rank(self.commands, query, self.recent)[:MAX_SHOWN]:
            item = QTreeWidgetItem([command.title, command.path, command.shortcut])
            item.setData(0, Qt.ItemDataRole.UserRole, command)
            item.setTextAlignment(2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item.setForeground(1, dim)
            if command.icon is not None:
                item.setIcon(0, command.icon)
            if not command.enabled:
                for column in range(3):
                    item.setForeground(column, dim)
                item.setToolTip(0, "Not available right now")
            self.list.addTopLevelItem(item)
        if self.list.topLevelItemCount():
            self.list.setCurrentItem(self.list.topLevelItem(0))

    def shown(self) -> list[Command]:
        """The listed commands, in order (tests)."""
        return [self.list.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole) for i in range(self.list.topLevelItemCount())]

    def run_current(self) -> bool:
        """Run the highlighted command (only when it is available); closes the palette."""
        item = self.list.currentItem()
        command: Command | None = item.data(0, Qt.ItemDataRole.UserRole) if item is not None else None
        if command is None or not command.enabled or command.run is None:
            return False
        self.accept()
        self.ran.emit(command.key)
        command.run()
        return True

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 - Qt override: keys of the query line
        if watched is self.query and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                row = self.list.indexOfTopLevelItem(self.list.currentItem()) + (1 if key == Qt.Key.Key_Down else -1)
                if 0 <= row < self.list.topLevelItemCount():
                    self.list.setCurrentItem(self.list.topLevelItem(row))
                return True
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.run_current()
                return True
            if key == Qt.Key.Key_Escape:
                self.reject()
                return True
        return super().eventFilter(watched, event)


__all__ = ["Command", "CommandPalette", "rank"]
