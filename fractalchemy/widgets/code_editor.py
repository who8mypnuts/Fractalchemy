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

from PySide6.QtCore import QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QKeyEvent, QPainter, QPixmap, QSyntaxHighlighter, QTextCharFormat, QTextCursor, QTextDocument
from PySide6.QtWidgets import QFrame, QLabel, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from ..scripting import completion as C
from ..scripting import docs as D
from .base_code_editor import INDENT, BaseCodeEditor, LineNumberArea

TAB_TRIGGER = re.compile(r"[\w.'\"]$")
AUTO_TRIGGER_LETTERS = 2
POPUP_ROWS = 9
POPUP_MIN_WIDTH = 300
DOC_WIDTH = 360

# Colours of the highlighter (a light scheme that reads on the default Qt palette)
COLORS = {
    "keyword": "#7b2fa0", "builtin": "#1565c0", "api": "#0d47a1", "member": "#8d5a00", "string": "#2e7d32", "comment": "#8a8a8a",
    "number": "#c45200", "decorator": "#7b2fa0", "definition": "#1565c0", "meta": "#4a7a48",
}
KIND_BADGES = {"function": ("f", "#3b5f9e"), "method": ("f", "#3b5f9e"), "property": ("p", "#9a6a1d"), "object": ("o", "#2f7a42"),
               "variable": ("v", "#9a6a1d"), "keyword": ("k", "#6a4a7a"), "constant": ("c", "#7a3a3a"), "option": ("\"", "#2a7a7a"),
               "argument": ("=", "#5a5a9a"), "module": ("m", "#2f7a42"), "class": ("C", "#2f7a42")}


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
# completion popup
# =====================================================================================================
def badge_pixmap(kind: str, size: int = 16) -> QPixmap:
    letter, color = KIND_BADGES.get(kind, ("?", "#666666"))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(color))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(1, 1, size - 2, size - 2, 3, 3)
    painter.setPen(QColor("#ffffff"))
    font = painter.font()
    font.setBold(True)
    font.setPixelSize(size - 5)
    painter.setFont(font)
    painter.drawText(QRect(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, letter)
    painter.end()
    return pixmap


def item_doc_html(item: C.Item) -> str:
    """The inline documentation shown beside the completion list."""
    from html import escape
    sig = item.sig or (f"{item.name}()" if item.kind in ("function", "method") else item.name + (f" : {item.type}" if item.type else ""))
    html = f"<div style='font-family: monospace; color: #0d47a1; font-weight: bold'>{escape(sig)}</div>"
    if item.desc:
        html += f"<div style='margin-top: 3px'>{escape(item.desc)}</div>"
    if item.detail:
        html += f"<div style='color: #777; margin-top: 3px'>parameters: {escape(item.detail)}</div>"
    if item.entry is not None and item.entry.example:
        html += f"<pre style='background: #f4f4f4; margin-top: 4px; padding: 3px'>{escape(item.entry.example)}</pre>"
    return html


class CompletionPopup(QFrame):
    """The list of candidates (a tool-tip style window that never takes the focus) plus the documentation box."""

    def __init__(self, editor: "CodeEditor"):
        super().__init__(editor, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._editor = editor
        self.list = QTreeWidget(self)
        self.list.setColumnCount(2)
        self.list.setHeaderHidden(True)
        self.list.setRootIsDecorated(False)
        self.list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.list.setUniformRowHeights(True)
        self.list.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.list.setIconSize(QSize(16, 16))
        self.list.itemClicked.connect(lambda *_: editor.accept_completion())
        self.list.currentItemChanged.connect(lambda *_: self._show_doc())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.addWidget(self.list)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.doc = QLabel(editor, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.doc.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.doc.setWordWrap(True)
        self.doc.setTextFormat(Qt.TextFormat.RichText)
        self.doc.setFrameShape(QFrame.Shape.StyledPanel)
        self.doc.setMargin(6)
        self.doc.setFixedWidth(DOC_WIDTH)
        self.doc.setStyleSheet("QLabel { background: #fffdf5; }")
        self.items: list[C.Item] = []

    def show_items(self, items: list[C.Item], at: QPoint) -> None:
        self.items = items
        self.list.clear()
        for item in items:
            row = QTreeWidgetItem([item.name, item.type or ""])
            row.setIcon(0, badge_pixmap(item.kind))
            row.setForeground(1, QColor("#777777"))
            font = row.font(0)
            font.setFamily(self._editor.font().family())
            row.setFont(0, font)
            self.list.addTopLevelItem(row)
        self.list.resizeColumnToContents(0)
        self.list.setCurrentItem(self.list.topLevelItem(0))
        rows = min(POPUP_ROWS, len(items))
        row_height = self.list.sizeHintForRow(0) if items else 20
        width = max(POPUP_MIN_WIDTH, self.list.columnWidth(0) + 120)
        self.resize(width, rows * row_height + 8)
        self.move(at)
        self.show()
        self._show_doc()

    def current(self) -> C.Item | None:
        index = self.list.indexOfTopLevelItem(self.list.currentItem())
        return self.items[index] if 0 <= index < len(self.items) else None

    def move_selection(self, delta: int) -> None:
        count = self.list.topLevelItemCount()
        if not count:
            return
        index = max(0, min(count - 1, self.list.indexOfTopLevelItem(self.list.currentItem()) + delta))
        self.list.setCurrentItem(self.list.topLevelItem(index))
        self.list.scrollToItem(self.list.topLevelItem(index))

    def _show_doc(self) -> None:
        item = self.current()
        if item is None or not self.isVisible():
            self.doc.hide()
            return
        self.doc.setText(item_doc_html(item))
        self.doc.adjustSize()
        x = self.x() + self.width() + 2
        screen = self.screen().availableGeometry() if self.screen() else QRect(0, 0, 100000, 100000)
        if x + DOC_WIDTH > screen.right():
            x = self.x() - DOC_WIDTH - 2
        self.doc.move(x, self.y())
        self.doc.show()

    def hideEvent(self, event) -> None:
        self.doc.hide()
        super().hideEvent(event)


# =====================================================================================================
# the editor
# =====================================================================================================
class CodeEditor(BaseCodeEditor):
    """Script editor widget: `BaseCodeEditor` plus Python highlighting, completion and indentation.

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
        self.popup = CompletionPopup(self)
        self._completion: C.Completion | None = None
        self._typing = False
        self._context_timer = QTimer(self, singleShot=True, interval=120)
        self._context_timer.timeout.connect(self.context_changed)

    # --- language hooks ----------------------------------------------------------------------------------
    def indent_after(self, line: str) -> bool:
        """A block opener: the line ends with `:` (and is not a comment)."""
        return line.endswith(":") and not line.lstrip().startswith("#")

    def dedent_line(self, line: str) -> bool:
        """A block closer: `return`, `pass`, `break`, `continue`, `raise`."""
        return re.match(r"\s*(return|pass|break|continue|raise)\b", line) is not None

    def _on_cursor_moved(self) -> None:
        super()._on_cursor_moved()
        self._context_timer.start()

    def _on_text_changed(self) -> None:
        super()._on_text_changed()
        self._context_timer.start()
        if self.popup.isVisible():
            self._refresh_completion()
        elif self._typing:
            self._maybe_auto_complete()
        self._typing = False

    # --- completion -------------------------------------------------------------------------------------------------
    def open_completion(self, explicit: bool = False) -> None:
        """Show candidates for the cursor position (`explicit`: Tab / Ctrl+Space — a single match is inserted at once)."""
        result = C.complete(self.toPlainText(), self.position, explicit)
        if not result.items:
            self.close_completion()
            if explicit:
                self.status.emit("No completions here")
            return
        if explicit and len(result.items) == 1 and result.items[0].text != result.prefix:
            self._completion = result
            self._insert_item(result.items[0])
            return
        if not explicit and len(result.items) == 1 and result.items[0].text == result.prefix:
            self.close_completion()
            return
        self._completion = result
        rect = self.cursorRect()
        at = self.viewport().mapToGlobal(QPoint(rect.left() - 20, rect.bottom() + 2))
        self.popup.show_items(result.items[:200], at)

    def _refresh_completion(self) -> None:
        result = C.complete(self.toPlainText(), self.position, False)
        if not result.items or (self._completion is not None and result.start != self._completion.start and not result.in_string):
            self.close_completion()
            if result.items:
                self.open_completion(False)
            return
        self._completion = result
        rect = self.cursorRect()
        at = self.viewport().mapToGlobal(QPoint(rect.left() - 20, rect.bottom() + 2))
        self.popup.show_items(result.items[:200], at)

    def _maybe_auto_complete(self) -> None:
        text = self.toPlainText()
        pos = self.position
        before = text[max(0, pos - 60):pos]
        m = re.search(r"(\w*)$", before)
        prefix = m.group(1) if m else ""
        trigger = before.endswith(".") or (len(prefix) >= AUTO_TRIGGER_LETTERS and before[-1:].isalnum()) or before.endswith(("'", '"', "["))
        if trigger:
            self.open_completion(False)

    def accept_completion(self) -> None:
        """Insert the candidate selected in the popup."""
        item = self.popup.current()
        if item is None or self._completion is None:
            self.close_completion()
            return
        self._insert_item(item)

    def _insert_item(self, item: C.Item) -> None:
        result = self._completion
        self.close_completion()
        if result is None:
            return
        start, end = result.start, self.position
        text = item.text
        cursor_offset = len(text)
        if item.kind in ("function", "method") and self.toPlainText()[end:end + 1] != "(":
            has_params = bool(item.entry and item.entry.params) or (item.sig and not item.sig.endswith("()"))
            text += "()"
            cursor_offset = len(text) - (1 if has_params else 0)
        if result.in_string:
            quote = self.toPlainText()[start - 1:start]
            if self.toPlainText()[end:end + 1] == quote:
                cursor_offset = len(text) + 1   # step over the closing quote
        cursor = self.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(text)
        cursor.setPosition(start + cursor_offset)
        self.setTextCursor(cursor)
        self.setFocus()
        if text.endswith("()") and cursor_offset == len(text) - 1:
            QTimer.singleShot(0, lambda: self._maybe_auto_complete())

    def close_completion(self) -> None:
        """Hide the popup."""
        if self.popup.isVisible():
            self.popup.hide()
        self._completion = None

    # --- keys ------------------------------------------------------------------------------------------------------
    def keyPressEvent(self, event: QKeyEvent) -> None:
        key, mods = event.key(), event.modifiers()
        ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
        if self.popup.isVisible():
            if key in (Qt.Key.Key_Down, Qt.Key.Key_Up, Qt.Key.Key_PageDown, Qt.Key.Key_PageUp):
                self.popup.move_selection({Qt.Key.Key_Down: 1, Qt.Key.Key_Up: -1, Qt.Key.Key_PageDown: POPUP_ROWS, Qt.Key.Key_PageUp: -POPUP_ROWS}[key])
                return
            if key == Qt.Key.Key_Escape:
                self.close_completion()
                return
            if key == Qt.Key.Key_Tab:
                self.accept_completion()
                return
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                item = self.popup.current()
                if item is not None and self._completion is not None and item.text != self._completion.prefix:
                    self.accept_completion()
                    return
                self.close_completion()
            if key in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Home, Qt.Key.Key_End):
                self.close_completion()
        if ctrl and key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.run_requested.emit()
            return
        if ctrl and key == Qt.Key.Key_Space:
            self.open_completion(True)
            return
        self._typing = bool(event.text()) and event.text().isprintable() and not ctrl   # printable keys may open the popup
        super().keyPressEvent(event)

    def _on_tab(self) -> None:
        """Tab: indent a multi-line selection, complete the word before the cursor, else insert indentation."""
        cursor = self.textCursor()
        if cursor.hasSelection() and "\u2029" in cursor.selectedText():
            self.indent()
            return
        before = cursor.block().text()[:cursor.positionInBlock()]
        if before.strip() and TAB_TRIGGER.search(before):
            self.open_completion(True)
            return
        cursor.insertText(INDENT)

    def focusOutEvent(self, event) -> None:
        QTimer.singleShot(150, self._close_if_unfocused)
        super().focusOutEvent(event)

    def _close_if_unfocused(self) -> None:
        if not self.hasFocus():
            self.close_completion()

    def mousePressEvent(self, event) -> None:
        self.close_completion()
        super().mousePressEvent(event)

    def wheelEvent(self, event) -> None:
        self.close_completion()
        super().wheelEvent(event)


__all__ = ["CodeEditor", "PythonHighlighter", "CompletionPopup", "LineNumberArea", "badge_pixmap", "item_doc_html"]
