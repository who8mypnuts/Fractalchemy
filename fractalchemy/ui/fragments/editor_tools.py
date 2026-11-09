"""Small helpers the fragment editor composes: inline diagnostics, snippet tab-stops and multi-selection editing.

Each is a plain object holding `QTextCursor`s (which follow the text as it changes) and knows nothing of the
editor's keys — `GlslCodeEditor` decides when to call them:

* `DiagnosticMarks` — the build's errors and warnings as wavy underlines on their lines, with the message as a hover
  tooltip (`message_at(line)`);
* `SnippetSession` — a snippet with `${1:placeholder}` / `$2` / `$0` stops: `expand` turns the template into plain
  text plus stop positions, the session selects them in turn (Tab), ending at `$0` or the snippet's end;
* `MultiSelection` — further cursors added with *select next occurrence*: a typed character, Backspace or Delete
  applies to every cursor (one undo step), so renaming a variable is Ctrl+Shift+D a few times and typing.
"""

from __future__ import annotations

import re

from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit

STOP = re.compile(r"\$\{(\d+):([^}]*)\}|\$(\d+)")


class DiagnosticMarks:
    """Wavy underlines for the compiler's remarks (see the module docstring)."""

    def __init__(self, editor: QPlainTextEdit):
        self._editor = editor
        self._items: list[tuple[int, str, str]] = []

    def set(self, items: list[tuple[int, str, str]]) -> None:
        """`(line, severity, message)` triples (1-based lines); an empty list clears the marks."""
        self._items = [(int(line), severity, message) for line, severity, message in items if line > 0]

    def clear(self) -> None:
        self._items = []

    @property
    def count(self) -> int:
        return len(self._items)

    def message_at(self, line: int) -> str | None:
        """Every remark on `line`, one per row, or None."""
        texts = [f"{severity}: {message}" for at, severity, message in self._items if at == line]
        return "\n".join(texts) if texts else None

    def selections(self) -> list[QTextEdit.ExtraSelection]:
        out = []
        document = self._editor.document()
        theme = self._editor.theme                       # the underline colours follow the editor's theme
        for line, severity, _message in self._items:
            block = document.findBlockByNumber(line - 1)
            if not block.isValid():
                continue
            text = block.text()
            if not text.strip():
                continue
            first = len(text) - len(text.lstrip())
            selection = QTextEdit.ExtraSelection()
            selection.format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
            selection.format.setUnderlineColor(QColor(theme["error" if severity == "error" else "warning"]))
            selection.cursor = QTextCursor(block)
            selection.cursor.setPosition(block.position() + first)
            selection.cursor.setPosition(block.position() + len(text), QTextCursor.MoveMode.KeepAnchor)
            out.append(selection)
        return out


class SnippetSession:
    """Tab-stops of an inserted snippet (see the module docstring)."""

    @staticmethod
    def expand(template: str) -> tuple[str, list[tuple[int, int, int]]]:
        """The template as plain text and its stops as `(index, offset, length)`, `$0` last."""
        out, stops, position = [], [], 0
        for match in STOP.finditer(template):
            out.append(template[position:match.start()])
            index = int(match.group(1) or match.group(3))
            placeholder = match.group(2) or ""
            offset = sum(len(part) for part in out)
            stops.append((index, offset, len(placeholder)))
            out.append(placeholder)
            position = match.end()
        out.append(template[position:])
        stops.sort(key=lambda stop: (stop[0] == 0, stop[0]))
        return "".join(out), stops

    def __init__(self, editor: QPlainTextEdit, base: int, stops: list[tuple[int, int, int]]):
        """Args:
            editor: The editor the snippet was inserted into.
            base: The character offset the snippet starts at.
            stops: `expand`'s stops.
        """
        self._editor = editor
        self._cursors: list[QTextCursor] = []
        for _index, offset, length in stops:
            cursor = QTextCursor(editor.document())
            cursor.setPosition(base + offset)
            cursor.setPosition(base + offset + length, QTextCursor.MoveMode.KeepAnchor)
            self._cursors.append(cursor)
        self._at = -1

    @property
    def active(self) -> bool:
        return 0 <= self._at < len(self._cursors) - 1 or (self._at == -1 and bool(self._cursors))

    def next(self) -> bool:
        """Select the next stop; False when there is none left (the session is over)."""
        self._at += 1
        if self._at >= len(self._cursors):
            self._at = len(self._cursors)
            return False
        cursor = QTextCursor(self._cursors[self._at])
        self._editor.setTextCursor(cursor)
        return True


class MultiSelection:
    """Extra cursors that edit together (see the module docstring)."""

    def __init__(self, editor: QPlainTextEdit):
        self._editor = editor
        self._cursors: list[QTextCursor] = []

    @property
    def active(self) -> bool:
        return bool(self._cursors)

    @property
    def count(self) -> int:
        return len(self._cursors) + 1

    def clear(self) -> None:
        self._cursors = []

    def add_next_occurrence(self) -> bool:
        """Select the next occurrence of the main selection (or the word under the cursor) as one more cursor."""
        main = self._editor.textCursor()
        if not main.hasSelection():
            main.select(QTextCursor.SelectionType.WordUnderCursor)
            if not main.hasSelection():
                return False
            self._editor.setTextCursor(main)
        needle = main.selectedText()
        document = self._editor.document()
        taken = [self._editor.textCursor()] + self._cursors
        start = max(c.selectionEnd() for c in taken)
        found = document.find(needle, start)
        if found.isNull():
            found = document.find(needle, 0)
        if found.isNull() or any(found.selectionStart() == c.selectionStart() for c in taken):
            return False
        self._cursors.append(found)
        return True

    def add_all_occurrences(self) -> int:
        while self.add_next_occurrence():
            pass
        return self.count

    def selections(self) -> list[QTextEdit.ExtraSelection]:
        out = []
        for cursor in self._cursors:
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(QColor(self._editor.theme["match"]))
            selection.cursor = QTextCursor(cursor)
            out.append(selection)
        return out

    def type_text(self, text: str) -> None:
        """Insert `text` at every cursor (replacing their selections) as one undo step."""
        self._edit(lambda cursor: cursor.insertText(text))

    def delete(self, backwards: bool) -> None:
        def act(cursor: QTextCursor) -> None:
            if cursor.hasSelection():
                cursor.removeSelectedText()
            elif backwards:
                cursor.deletePreviousChar()
            else:
                cursor.deleteChar()
        self._edit(act)

    def _edit(self, act) -> None:
        main = self._editor.textCursor()
        main.beginEditBlock()
        act(main)
        for cursor in self._cursors:
            act(cursor)
        main.endEditBlock()
        self._editor.setTextCursor(main)


def word_at(editor: QPlainTextEdit, position: int) -> str:
    """The identifier around character `position` (empty when none)."""
    cursor = QTextCursor(editor.document())
    cursor.setPosition(position)
    cursor.select(QTextCursor.SelectionType.WordUnderCursor)
    word = cursor.selectedText()
    return word if re.fullmatch(r"[A-Za-z_]\w*", word or "") else ""


__all__ = ["DiagnosticMarks", "SnippetSession", "MultiSelection", "word_at"]
