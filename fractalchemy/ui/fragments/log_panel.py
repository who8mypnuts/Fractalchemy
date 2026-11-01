"""The Log dock: the preprocessor's and the compiler's remarks, with clickable `file:line` references.

FragM's `ListWidgetLogger`: one row per message, coloured by level (info / warning / critical / script), a context
menu to copy or clear, a cap on the number of rows. A row that knows its file and line is underlined and emits
`location_activated(path, line)` when clicked, so the window can open the file (a bundled include read-only) and
centre the line — FragM's *jump to line on error*. With `set_log_file` every row is also appended to a text file
(FragM's *log to file*), rotated to `.1` once it passes the size cap.
"""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QMenu, QWidget

from ...fragments.source import Message

LEVEL_COLORS = {"info": QColor(90, 90, 90), "warning": QColor(170, 100, 0), "critical": QColor(190, 40, 40), "script": QColor(40, 110, 170),
                "error": QColor(190, 40, 40)}
MAX_ROWS = 2000
ROLE_PATH = Qt.ItemDataRole.UserRole
ROLE_LINE = Qt.ItemDataRole.UserRole + 1


class LogPanel(QListWidget):
    """The message list (see the module docstring).

    Signals:
        location_activated(object, int): (`Path`, line) of a clicked row that has a source location.
    """
    location_activated = Signal(object, int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.max_rows = MAX_ROWS
        self._log_file: Path | None = None
        self._log_max_bytes = 0
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)
        self.itemActivated.connect(self._activate)
        self.itemClicked.connect(self._activate)

    def add(self, level: str, text: str, path: Path | None = None, line: int = 0) -> None:
        """Append one row."""
        prefix = {"warning": "⚠ ", "critical": "✖ ", "error": "✖ ", "script": "▸ "}.get(level, "")
        where = f"{Path(path).name}:{line} — " if path is not None and line else ""
        if level == "warning" and self._recently_logged(f"{prefix}{where}{text}"):
            return                                   # the same warning again (a preset re-applied): once is enough
        item = QListWidgetItem(f"{prefix}{where}{text}")
        item.setForeground(LEVEL_COLORS.get(level, LEVEL_COLORS["info"]))
        if path is not None and line:
            item.setData(ROLE_PATH, str(path))
            item.setData(ROLE_LINE, int(line))
            font = item.font()
            font.setUnderline(True)
            item.setFont(font)
            item.setToolTip(f"Click to open {path} at line {line}")
        self.addItem(item)
        while self.count() > self.max_rows:
            self.takeItem(0)
        self.scrollToBottom()
        self._mirror(level, item.text())

    # --- log to file ------------------------------------------------------------------------------------------------------
    def set_log_file(self, path: Path | None, max_bytes: int = 1 << 20) -> None:
        """Mirror every row to `path` (None stops it); the file rotates to `<name>.1` once it passes `max_bytes`."""
        self._log_file, self._log_max_bytes = path, max(1024, int(max_bytes))
        if path is not None:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
            except OSError:
                self._log_file = None

    def _mirror(self, level: str, text: str) -> None:
        if self._log_file is None:
            return
        try:
            if self._log_file.exists() and self._log_file.stat().st_size > self._log_max_bytes:
                self._log_file.replace(self._log_file.with_name(self._log_file.name + ".1"))
            with self._log_file.open("a", encoding="utf-8") as handle:
                handle.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} [{level}] {text}\n")
        except OSError:
            self._log_file = None

    def _recently_logged(self, text: str, window: int = 12) -> bool:
        return any(self.item(i).text() == text for i in range(max(0, self.count() - window), self.count()))

    def add_message(self, message: Message) -> None:
        self.add(message.level, message.text, message.file, message.line)

    def add_diagnostics(self, diagnostics: list) -> None:
        """Compiler `Diagnostic`s (or preprocessor `Message`s) after a failed build."""
        for item in diagnostics:
            if isinstance(item, Message):
                self.add_message(item)
            else:
                text = item.message + (f"   [{item.source_line}]" if item.source_line else "")
                self.add("critical" if item.severity == "error" else "warning", f"{item.stage} shader: {text}", item.file, item.line)

    def _activate(self, item: QListWidgetItem) -> None:
        path = item.data(ROLE_PATH)
        if path:
            self.location_activated.emit(Path(path), int(item.data(ROLE_LINE)))

    def _menu(self, pos) -> None:
        menu = QMenu(self)
        copy = menu.addAction("Copy")
        copy_all = menu.addAction("Copy all")
        clear = menu.addAction("Clear")
        choice = menu.exec(self.mapToGlobal(pos))
        if choice is copy:
            QGuiApplication.clipboard().setText("\n".join(i.text() for i in self.selectedItems()))
        elif choice is copy_all:
            QGuiApplication.clipboard().setText("\n".join(self.item(i).text() for i in range(self.count())))
        elif choice is clear:
            self.clear()

    def texts(self) -> list[str]:
        """Every row's text (tests)."""
        return [self.item(i).text() for i in range(self.count())]


__all__ = ["LogPanel"]
