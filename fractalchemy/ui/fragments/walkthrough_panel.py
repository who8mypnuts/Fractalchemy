"""The Walkthrough dock: a fragment's `// STEP n:` comments as a clickable list, and below them its outline.

The tutorial fragments (`Examples/Fractalchemy Tutorials`) explain themselves in numbered step comments; this pane
lists them so a reader can jump from step to step (click → the editor scrolls to the line). Every fragment gets an
outline under the steps — its `#group`s, functions and `#preset`s with their lines — which is the quickest way around
a long include-based fragment. Refreshed a moment after the text changes.
"""

from __future__ import annotations

import re

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from ...fragments.definitions import all_definitions
from ...widgets.theming import on_theme_changed, theme_color

RE_STEP = re.compile(r"^\s*//\s*STEP\s*(\d+)\s*:\s*(.*)$", re.IGNORECASE)
RE_GROUP = re.compile(r"^\s*#group\s+(.*?)\s*$", re.IGNORECASE)
RE_PRESET = re.compile(r"^\s*#preset\s+(.*?)\s*$", re.IGNORECASE)
REFRESH_MS = 600
LINE_ROLE = Qt.ItemDataRole.UserRole + 1


def steps_of(text: str) -> list[tuple[int, int, str]]:
    """`(number, line, title)` for every `// STEP n: title` comment, in order of appearance."""
    out = []
    for number, line in enumerate(text.split("\n"), start=1):
        match = RE_STEP.match(line)
        if match:
            out.append((int(match.group(1)), number, match.group(2).strip()))
    return out


def outline_of(text: str) -> list[tuple[str, int, str]]:
    """`(kind, line, label)` for the groups, functions and presets of `text`, by line."""
    out = []
    for number, line in enumerate(text.split("\n"), start=1):
        match = RE_GROUP.match(line)
        if match:
            out.append(("group", number, match.group(1)))
        match = RE_PRESET.match(line)
        if match:
            out.append(("preset", number, match.group(1)))
    out += [("function", d.line, d.signature) for d in all_definitions(text) if d.kind == "function"]
    return sorted(out, key=lambda item: item[1])


class WalkthroughPanel(QWidget):
    """Steps and outline of the current fragment (see the module docstring).

    Signals:
        line_activated(int): A row was clicked: show this line.
    """
    line_activated = Signal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.summary = QLabel("No fragment", self)
        self.summary.setWordWrap(True)
        self.list = QListWidget(self)
        self.list.setAlternatingRowColors(True)
        self.list.itemClicked.connect(self._on_clicked)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.summary)
        layout.addWidget(self.list, 1)
        self._text_provider = lambda: None
        self._timer = QTimer(self, singleShot=True, interval=REFRESH_MS)
        self._timer.timeout.connect(self.refresh)
        on_theme_changed(self, lambda _theme: self.refresh())

    def bind(self, text_provider) -> None:
        """`text_provider()` returns the current document's text (None when there is no tab)."""
        self._text_provider = text_provider
        self.refresh()

    def schedule_refresh(self) -> None:
        self._timer.start()

    def refresh(self) -> None:
        text = self._text_provider()
        self.list.clear()
        if text is None:
            self.summary.setText("No fragment")
            return
        steps, outline = steps_of(text), outline_of(text)
        for number, line, title in steps:
            item = QListWidgetItem(f"Step {number}: {title}")
            item.setData(LINE_ROLE, line)
            item.setForeground(theme_color("link"))        # steps read as links (the theme's link colour)
            self.list.addItem(item)
        if steps and outline:
            separator = QListWidgetItem("— outline —")
            separator.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list.addItem(separator)
        for kind, line, label in outline:
            item = QListWidgetItem({"group": "▸ ", "preset": "◆ ", "function": "ƒ "}[kind] + label)
            item.setData(LINE_ROLE, line)
            item.setToolTip(f"{kind}, line {line}")
            if kind == "group":
                font = QFont()
                font.setBold(True)
                item.setFont(font)
            self.list.addItem(item)
        self.summary.setText((f"{len(steps)} steps · " if steps else "A fragment with STEP comments lists its steps here · ")
                             + f"{sum(1 for k, _l, _t in outline if k == 'function')} functions, {sum(1 for k, _l, _t in outline if k == 'group')} groups, "
                             f"{sum(1 for k, _l, _t in outline if k == 'preset')} presets")

    def _on_clicked(self, item: QListWidgetItem) -> None:
        line = item.data(LINE_ROLE)
        if line:
            self.line_activated.emit(int(line))


__all__ = ["WalkthroughPanel", "steps_of", "outline_of"]
