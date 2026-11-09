"""*Compare with original…*: the tab's text against the bundled example it came from (or its file on disk), with *Revert*.

An example saved under the user's own name remembers its origin (`metadata.tabs["origin"]`), so after an hour of
tweaking a Mandelbulb the diff shows exactly what changed; an unsaved bundled tab compares against the file, and
any other tab against its saved copy. The diff is `difflib`'s unified diff coloured line by line in a read-only
editor; *Revert to original* replaces the tab's text (one undoable edit).
"""

from __future__ import annotations

import difflib
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QPlainTextEdit, QVBoxLayout, QWidget

from ...widgets.base_code_editor import BaseCodeEditor

DIFF_ROLES = {"@@": "info", "---": "info", "+++": "info", "+": "success", "-": "error"}   # line prefix → theme role


def unified_diff(original: str, current: str, original_name: str, current_name: str) -> list[str]:
    """The unified diff lines between two texts (empty when identical)."""
    return list(difflib.unified_diff(original.splitlines(), current.splitlines(), original_name, current_name, lineterm="", n=3))


class DiffView(BaseCodeEditor):
    """A read-only editor showing a unified diff with coloured lines."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._lines: list[str] = []

    def apply_theme(self) -> None:
        """Recolour the editor, then the diff's lines (their colours are theme roles)."""
        super().apply_theme()
        if getattr(self, "_lines", None):
            self.show_diff(self._lines)                 # the line colours are the theme's

    def show_diff(self, lines: list[str]) -> None:
        """Show a unified diff, coloured: headers (info), added (success), removed (error)."""
        self._lines = list(lines)
        self.set_text("\n".join(lines))
        cursor = QTextCursor(self.document())
        block = self.document().firstBlock()
        while block.isValid():
            text = block.text()
            role = next((DIFF_ROLES[prefix] for prefix in DIFF_ROLES if text.startswith(prefix)), None)   # longest prefixes first
            if role is not None:
                fmt = QTextCharFormat()
                fmt.setForeground(QColor(self.theme[role]))
                cursor.setPosition(block.position())
                cursor.setPosition(block.position() + len(text), QTextCursor.MoveMode.KeepAnchor)
                cursor.setCharFormat(fmt)
            block = block.next()


class DiffDialog(QDialog):
    """The comparison window (see the module docstring).

    Signals:
        revert_requested(str): *Revert to original* — the text to put into the tab.
    """
    revert_requested = Signal(str)

    def __init__(self, parent: QWidget | None, original: str, current: str, original_name: str, current_name: str, original_path: Path | None):
        super().__init__(parent)
        self.setWindowTitle(f"Compare {current_name} with {original_name}")
        self.original = original
        lines = unified_diff(original, current, original_name, current_name)
        added = sum(1 for line in lines if line.startswith("+") and not line.startswith("+++"))
        removed = sum(1 for line in lines if line.startswith("-") and not line.startswith("---"))
        self.summary = QLabel(("The texts are identical" if not lines else f"{added} lines added, {removed} removed")
                              + (f" — original: {original_path}" if original_path else ""), self)
        self.summary.setWordWrap(True)
        self.view = DiffView(self)
        self.view.show_diff(lines if lines else ["(no differences)"])
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        self.revert_button = buttons.addButton("Revert to original", QDialogButtonBox.ButtonRole.ActionRole)
        self.revert_button.setEnabled(bool(lines))
        self.revert_button.clicked.connect(self._revert)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(self.summary)
        layout.addWidget(self.view, 1)
        layout.addWidget(buttons)
        self.resize(1000, 700)

    def _revert(self) -> None:
        self.revert_requested.emit(self.original)
        self.accept()


__all__ = ["DiffDialog", "DiffView", "unified_diff"]
