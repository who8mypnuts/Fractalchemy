"""The Script Editor's code editor: the line-numbered `BaseCodeEditor` with Python syntax highlighting that knows the
scripting API, a completion popup with inline documentation, and Python's indentation rules.

Completion candidates come from `fractalchemy.scripting.completion`; the editor only shows them:

* **Tab** completes the word (or opens the list when several names match); **Ctrl+Space** opens it anywhere.
* The list also opens by itself after a `.`, an opening quote inside a call, and once two letters of a name
  are typed. **Enter** / **Tab** accept, **Esc** closes; typing keeps filtering.
* Auto-indent after `:`; the line edits (indent / outdent, Ctrl+/ comments, Ctrl+D duplicates, Ctrl+Shift+K
  deletes, Alt+Up / Alt+Down move) come from `BaseCodeEditor`.
"""

from __future__ import annotations

import re

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QKeyEvent, QSyntaxHighlighter, QTextCharFormat, QTextDocument
from PySide6.QtWidgets import QWidget

from ..scripting import completion as C
from ..scripting import docs as D
from .base_code_editor import BaseCodeEditor, LineNumberArea
from .completion_popup import CompletionPopup, badge_pixmap, item_doc_html

AUTO_TRIGGER_LETTERS = 2

# Colours of the highlighter (a light scheme that reads on the default Qt palette)
COLORS = {
    "keyword": "#7b2fa0", "builtin": "#1565c0", "api": "#0d47a1", "member": "#8d5a00", "string": "#2e7d32", "comment": "#8a8a8a",
    "number": "#c45200", "decorator": "#7b2fa0", "definition": "#1565c0", "meta": "#4a7a48",
}


# =====================================================================================================
# highlighter
# =====================================================================================================
class PythonHighlighter(QSyntaxHighlighter):
    """Python colouring with the scripting API's globals and members picked out."""
    IN_TRIPLE_SINGLE, IN_TRIPLE_DOUBLE = 1, 2

    def __init__(self, document: QTextDocument):
        super().__init__(document)
        self._formats = {name: self._format(color, bold=name in ("keyword", "api", "definition")) for name, color in COLORS.items()}
        self._formats["comment"].setFontItalic(True)
        self._keywords = set(C.KEYWORDS)
        self._builtins = set(C.BUILTINS)
        self._api = set(D.GLOBALS)
        self._members = {name for doc in D.TYPES.values() for name in doc.members}
        self._word = re.compile(r"[A-Za-z_]\w*")
        self._number = re.compile(r"\b\d+(?:\.\d*)?(?:e[+-]?\d+)?\b|\b0x[0-9a-fA-F]+\b")

    @staticmethod
    def _format(color: str, bold: bool = False) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if bold:
            fmt.setFontWeight(QFont.Weight.Bold)
        return fmt

    def highlightBlock(self, text: str) -> None:
        state = self.previousBlockState()
        i = 0
        n = len(text)
        quote = {self.IN_TRIPLE_SINGLE: "'''", self.IN_TRIPLE_DOUBLE: '"""'}.get(state)
        if quote:
            end = text.find(quote)
            if end < 0:
                self.setFormat(0, n, self._formats["string"])
                self.setCurrentBlockState(state)
                return
            self.setFormat(0, end + 3, self._formats["string"])
            i = end + 3
        self.setCurrentBlockState(0)
        code_start = i
        while i < n:
            ch = text[i]
            if ch == "#":
                self._highlight_code(text, code_start, i)
                fmt = self._formats["meta"] if re.match(r"\s*#\s*@\w+", text) else self._formats["comment"]
                self.setFormat(i, n - i, fmt)
                return
            if ch in "\"'":
                self._highlight_code(text, code_start, i)
                triple = text.startswith(ch * 3, i)
                q = ch * 3 if triple else ch
                j = i + len(q)
                while j < n:
                    if text[j] == "\\":
                        j += 2
                        continue
                    if text.startswith(q, j):
                        j += len(q)
                        break
                    j += 1
                else:
                    if triple:
                        self.setCurrentBlockState(self.IN_TRIPLE_SINGLE if ch == "'" else self.IN_TRIPLE_DOUBLE)
                    j = n
                self.setFormat(i, j - i, self._formats["string"])
                i = j
                code_start = i
                continue
            i += 1
        self._highlight_code(text, code_start, n)

    def _highlight_code(self, text: str, start: int, end: int) -> None:
        segment = text[start:end]
        for m in self._number.finditer(segment):
            self.setFormat(start + m.start(), m.end() - m.start(), self._formats["number"])
        prev_def = False
        for m in self._word.finditer(segment):
            word = m.group(0)
            at = start + m.start()
            before = segment[:m.start()].rstrip()
            after_dot = before.endswith(".")
            if prev_def:
                fmt = "definition"
            elif after_dot:
                fmt = "member" if word in self._members else None
            elif word in self._keywords:
                fmt = "keyword"
            elif word in self._api:
                fmt = "api"
            elif word in self._builtins:
                fmt = "builtin"
            else:
                fmt = None
            if fmt:
                self.setFormat(at, len(word), self._formats[fmt])
            prev_def = word in ("def", "class") and not after_dot
        for m in re.finditer(r"@\w+", segment):
            self.setFormat(start + m.start(), m.end() - m.start(), self._formats["decorator"])


# =====================================================================================================
# the editor
# =====================================================================================================
class CodeEditor(BaseCodeEditor):
    """Script editor widget: `BaseCodeEditor` plus Python highlighting, the scripting completer and Python indentation.

    Signals (in addition to the base class's):
        run_requested(): Ctrl+Enter.
        context_changed(): The cursor moved or the text changed (debounced) — the help panel re-reads the position.
    """
    run_requested = Signal()
    context_changed = Signal()
    comment_prefix = "#"

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setPlaceholderText("# Type a script, or pick a template from the drawer on the right.\n# Tab completes names; Ctrl+Enter runs.")
        self.highlighter = PythonHighlighter(self.document())
        self.completer = C.complete
        self._context_timer = QTimer(self, singleShot=True, interval=120)
        self._context_timer.timeout.connect(self.context_changed)

    # --- language hooks ----------------------------------------------------------------------------------
    def indent_after(self, line: str) -> bool:
        """A block opener: the line ends with `:` (and is not a comment)."""
        return line.endswith(":") and not line.lstrip().startswith("#")

    def dedent_line(self, line: str) -> bool:
        """A block closer: `return`, `pass`, `break`, `continue`, `raise`."""
        return re.match(r"\s*(return|pass|break|continue|raise)\b", line) is not None

    def auto_complete_trigger(self, before: str, prefix: str) -> bool:
        """After a `.`, an opening quote or bracket, or once two letters of a name are typed."""
        return before.endswith(".") or (len(prefix) >= AUTO_TRIGGER_LETTERS and before[-1:].isalnum()) or before.endswith(("'", '"', "["))

    def _on_cursor_moved(self) -> None:
        super()._on_cursor_moved()
        self._context_timer.start()

    def _on_text_changed(self) -> None:
        super()._on_text_changed()
        self._context_timer.start()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.run_requested.emit()
            return
        super().keyPressEvent(event)


__all__ = ["CodeEditor", "PythonHighlighter", "CompletionPopup", "LineNumberArea", "badge_pixmap", "item_doc_html"]
