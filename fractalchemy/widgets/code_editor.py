"""The Script Editor's code editor: a QPlainTextEdit with line numbers, Python syntax highlighting that knows the
scripting API, a completion popup with inline documentation, and the usual editing conveniences.

Completion candidates come from `fractalchemy.scripting.completion`; the editor only shows them:

* **Tab** completes the word (or opens the list when several names match); **Ctrl+Space** opens it anywhere.
* The list also opens by itself after a `.`, an opening quote inside a call, and once two letters of a name
  are typed. **Enter** / **Tab** accept, **Esc** closes; typing keeps filtering.
* Auto-indent after `:`; Tab / Shift+Tab indent or outdent a selection; Backspace eats a level of indentation;
  Ctrl+/ toggles `#` comments; Ctrl+D duplicates the line; Ctrl+Shift+K deletes it; Alt+Up / Alt+Down move it.
"""

from __future__ import annotations

import re

from PySide6.QtCore import QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor, QFont, QFontDatabase, QKeyEvent, QPainter, QPaintEvent, QPixmap, QResizeEvent, QSyntaxHighlighter, QTextCharFormat,
    QTextCursor, QTextDocument, QTextFormat,
)
from PySide6.QtWidgets import (
    QFrame, QLabel, QPlainTextEdit, QTextEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from ..scripting import completion as C
from ..scripting import docs as D

INDENT = "    "
TAB_TRIGGER = re.compile(r"[\w.'\"]$")
AUTO_TRIGGER_LETTERS = 2
POPUP_ROWS = 9
POPUP_MIN_WIDTH = 300
DOC_WIDTH = 360
LINE_NUMBER_PADDING = 10

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
class LineNumberArea(QWidget):
    def __init__(self, editor: "CodeEditor"):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor.line_number_width(), 0)

    def paintEvent(self, event: QPaintEvent) -> None:
        self._editor.paint_line_numbers(event)


class CodeEditor(QPlainTextEdit):
    """Script editor widget.

    Signals:
        run_requested(): Ctrl+Enter.
        find_requested(bool): Ctrl+F (False) / Ctrl+H (True: replace).
        goto_requested(): Ctrl+G.
        save_requested(bool): Ctrl+S (False) / Ctrl+Shift+S (True: save as).
        context_changed(): The cursor moved or the text changed (debounced) — the help panel re-reads the position.
        status(str): A short note for the status bar.
    """
    run_requested = Signal()
    find_requested = Signal(bool)
    goto_requested = Signal()
    save_requested = Signal(bool)
    context_changed = Signal()
    status = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        font.setPointSize(max(10, font.pointSize()))
        self.setFont(font)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setPlaceholderText("# Type a script, or pick a template from the drawer on the right.\n# Tab completes names; Ctrl+Enter runs.")
        self.highlighter = PythonHighlighter(self.document())
        self._numbers = LineNumberArea(self)
        self._error_line: int | None = None
        self.popup = CompletionPopup(self)
        self._completion: C.Completion | None = None
        self._context_timer = QTimer(self, singleShot=True, interval=120)
        self._context_timer.timeout.connect(self.context_changed)
        self.blockCountChanged.connect(lambda _n: self._update_margins())
        self.updateRequest.connect(self._update_numbers)
        self.cursorPositionChanged.connect(self._on_cursor_moved)
        self.textChanged.connect(self._on_text_changed)
        self._update_margins()
        self._highlight_lines()

    # --- line numbers ------------------------------------------------------------------------------------
    def line_number_width(self) -> int:
        digits = max(2, len(str(max(1, self.blockCount()))))
        return LINE_NUMBER_PADDING + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_margins(self) -> None:
        self.setViewportMargins(self.line_number_width(), 0, 0, 0)

    def _update_numbers(self, rect: QRect, dy: int) -> None:
        if dy:
            self._numbers.scroll(0, dy)
        else:
            self._numbers.update(0, rect.y(), self._numbers.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_margins()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        rect = self.contentsRect()
        self._numbers.setGeometry(QRect(rect.left(), rect.top(), self.line_number_width(), rect.height()))

    def paint_line_numbers(self, event: QPaintEvent) -> None:
        painter = QPainter(self._numbers)
        painter.fillRect(event.rect(), self.palette().window().color())
        block = self.firstVisibleBlock()
        number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        current = self.textCursor().blockNumber()
        width = self._numbers.width() - 4
        height = self.fontMetrics().height()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                if number + 1 == self._error_line:
                    painter.setPen(QColor("#c62828"))
                elif number == current:
                    painter.setPen(self.palette().text().color())
                else:
                    painter.setPen(QColor("#8a8a8a"))
                painter.drawText(0, top, width, height, Qt.AlignmentFlag.AlignRight, str(number + 1))
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            number += 1

    # --- state ---------------------------------------------------------------------------------------------
    def text(self) -> str:
        return self.toPlainText()

    def set_text(self, text: str) -> None:
        """Replace the contents (clears the undo history and any error mark)."""
        self.setPlainText(text)
        self.document().clearUndoRedoStacks()
        self.set_error_line(None)
        self.moveCursor(QTextCursor.MoveOperation.Start)

    @property
    def position(self) -> int:
        return self.textCursor().position()

    def line_column(self) -> tuple[int, int]:
        cursor = self.textCursor()
        return cursor.blockNumber() + 1, cursor.positionInBlock() + 1

    def goto_line(self, line: int, column: int = 1) -> None:
        block = self.document().findBlockByNumber(max(0, min(self.blockCount() - 1, line - 1)))
        cursor = QTextCursor(block)
        cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, max(0, min(column - 1, block.length() - 1)))
        self.setTextCursor(cursor)
        self.centerCursor()
        self.setFocus()

    def set_error_line(self, line: int | None) -> None:
        self._error_line = line
        self._highlight_lines()
        self._numbers.update()

    @property
    def error_line(self) -> int | None:
        return self._error_line

    def _highlight_lines(self) -> None:
        selections = []
        current = QTextEdit.ExtraSelection()
        current.format.setBackground(QColor(0, 0, 0, 12) if self.palette().base().color().lightness() > 128 else QColor(255, 255, 255, 14))
        current.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        current.cursor = self.textCursor()
        current.cursor.clearSelection()
        selections.append(current)
        if self._error_line is not None:
            error = QTextEdit.ExtraSelection()
            error.format.setBackground(QColor(255, 80, 80, 50))
            error.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            error.cursor = QTextCursor(self.document().findBlockByNumber(self._error_line - 1))
            selections.append(error)
        self.setExtraSelections(selections)

    def _on_cursor_moved(self) -> None:
        self._highlight_lines()
        self._numbers.update()
        self._context_timer.start()

    def _on_text_changed(self) -> None:
        if self._error_line is not None:
            self.set_error_line(None)
        self._context_timer.start()
        if self.popup.isVisible():
            self._refresh_completion()
        elif self._typing:
            self._maybe_auto_complete()
        self._typing = False

    _typing = False

    # --- editing helpers -------------------------------------------------------------------------------------
    def _selected_block_range(self) -> tuple[int, int]:
        cursor = self.textCursor()
        start = self.document().findBlock(cursor.selectionStart()).blockNumber()
        end_pos = cursor.selectionEnd()
        end_block = self.document().findBlock(end_pos)
        if cursor.hasSelection() and end_block.position() == end_pos and end_pos > cursor.selectionStart():
            end_block = end_block.previous()   # a selection ending at a line start does not include that line
        return start, end_block.blockNumber()

    def _map_lines(self, fn) -> None:
        """Replace the selected lines by `fn(line)` each, keeping them selected."""
        first, last = self._selected_block_range()
        doc = self.document()
        cursor = QTextCursor(doc.findBlockByNumber(first))
        cursor.beginEditBlock()
        for number in range(first, last + 1):
            block = doc.findBlockByNumber(number)
            text = block.text()
            new = fn(text)
            if new != text:
                c = QTextCursor(block)
                c.select(QTextCursor.SelectionType.LineUnderCursor)
                c.insertText(new)
        cursor.endEditBlock()
        start_block, end_block = doc.findBlockByNumber(first), doc.findBlockByNumber(last)
        selection = QTextCursor(start_block)
        selection.setPosition(end_block.position() + end_block.length() - 1, QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(selection)

    def indent(self) -> None:
        self._map_lines(lambda line: INDENT + line if line.strip() else line)

    def outdent(self) -> None:
        self._map_lines(lambda line: line[len(INDENT):] if line.startswith(INDENT) else line.lstrip(" ") if line[:1] == " " else line[1:] if line[:1] == "\t" else line)

    def toggle_comment(self) -> None:
        first, last = self._selected_block_range()
        lines = [self.document().findBlockByNumber(n).text() for n in range(first, last + 1)]
        content = [line for line in lines if line.strip()]
        all_commented = bool(content) and all(line.lstrip().startswith("#") for line in content)
        if all_commented:
            self._map_lines(lambda line: re.sub(r"^(\s*)#\s?", r"\1", line, count=1))
        else:
            width = min((len(line) - len(line.lstrip()) for line in content), default=0)
            self._map_lines(lambda line: line[:width] + "# " + line[width:] if line.strip() else line)

    def duplicate_line(self) -> None:
        cursor = self.textCursor()
        column = cursor.positionInBlock()
        block = cursor.block()
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
        cursor.insertText("\n" + block.text())
        cursor.endEditBlock()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, column)
        self.setTextCursor(cursor)

    def delete_line(self) -> None:
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
        cursor.removeSelectedText()
        cursor.deleteChar() if cursor.atStart() else None
        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def move_line(self, delta: int) -> None:
        cursor = self.textCursor()
        block = cursor.block()
        other = block.previous() if delta < 0 else block.next()
        if not other.isValid():
            return
        column = cursor.positionInBlock()
        text, other_text = block.text(), other.text()
        cursor.beginEditBlock()
        c = QTextCursor(block)
        c.select(QTextCursor.SelectionType.LineUnderCursor)
        c.insertText(other_text)
        c = QTextCursor(other)
        c.select(QTextCursor.SelectionType.LineUnderCursor)
        c.insertText(text)
        cursor.endEditBlock()
        target = QTextCursor(self.document().findBlockByNumber(other.blockNumber()))
        target.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, min(column, len(text)))
        self.setTextCursor(target)

    def insert_snippet(self, text: str) -> None:
        """Insert `text` at the cursor (indented to the current line's level) and keep the focus."""
        cursor = self.textCursor()
        line = cursor.block().text()[:cursor.positionInBlock()]
        indent = line[:len(line) - len(line.lstrip())] if not line.strip() else ""
        cursor.insertText(text.replace("\n", "\n" + indent) if indent else text)
        self.setFocus()

    def replace_range(self, start: int, end: int, text: str) -> None:
        cursor = self.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(text)
        self.setTextCursor(cursor)

    def selected_text(self) -> str:
        return self.textCursor().selectedText().replace("\u2029", "\n")

    # --- find / replace ------------------------------------------------------------------------------------------
    def find_text(self, needle: str, backwards: bool = False, case_sensitive: bool = False) -> bool:
        """Select the next (or previous) match, wrapping around; False if there is none."""
        if not needle:
            return False
        flags = QTextDocument.FindFlag(0)
        if backwards:
            flags |= QTextDocument.FindFlag.FindBackward
        if case_sensitive:
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if self.find(needle, flags):
            return True
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End if backwards else QTextCursor.MoveOperation.Start)
        self.setTextCursor(cursor)
        return self.find(needle, flags)

    def count_matches(self, needle: str, case_sensitive: bool = False) -> int:
        if not needle:
            return 0
        hay = self.toPlainText()
        return hay.count(needle) if case_sensitive else hay.lower().count(needle.lower())

    def replace_current(self, needle: str, replacement: str, case_sensitive: bool = False) -> bool:
        selected = self.selected_text()
        if needle and (selected == needle if case_sensitive else selected.lower() == needle.lower()):
            self.textCursor().insertText(replacement)
        return self.find_text(needle, False, case_sensitive)

    def replace_all(self, needle: str, replacement: str, case_sensitive: bool = False) -> int:
        count = self.count_matches(needle, case_sensitive)
        if not count:
            return 0
        pattern = re.compile(re.escape(needle), 0 if case_sensitive else re.IGNORECASE)
        text = pattern.sub(lambda _m: replacement, self.toPlainText())
        cursor = self.textCursor()
        position = cursor.position()
        cursor.beginEditBlock()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.insertText(text)
        cursor.endEditBlock()
        cursor.setPosition(min(position, len(text)))
        self.setTextCursor(cursor)
        return count

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
        if self.popup.isVisible():
            self.popup.hide()
        self._completion = None

    # --- keys ------------------------------------------------------------------------------------------------------
    def keyPressEvent(self, event: QKeyEvent) -> None:
        key, mods = event.key(), event.modifiers()
        ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
        shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)
        alt = bool(mods & Qt.KeyboardModifier.AltModifier)
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
        if ctrl and key == Qt.Key.Key_Slash:
            self.toggle_comment()
            return
        if ctrl and key == Qt.Key.Key_D:
            self.duplicate_line()
            return
        if ctrl and shift and key == Qt.Key.Key_K:
            self.delete_line()
            return
        if ctrl and key == Qt.Key.Key_BracketRight:
            self.indent()
            return
        if ctrl and key == Qt.Key.Key_BracketLeft:
            self.outdent()
            return
        if alt and key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            self.move_line(-1 if key == Qt.Key.Key_Up else 1)
            return
        if ctrl and key == Qt.Key.Key_F:
            self.find_requested.emit(False)
            return
        if ctrl and key == Qt.Key.Key_H:
            self.find_requested.emit(True)
            return
        if ctrl and key == Qt.Key.Key_G:
            self.goto_requested.emit()
            return
        if ctrl and key == Qt.Key.Key_S:
            self.save_requested.emit(shift)
            return
        if key == Qt.Key.Key_Tab and not ctrl:
            self._on_tab()
            return
        if key == Qt.Key.Key_Backtab:
            self.outdent()
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not ctrl:
            self._on_return()
            return
        if key == Qt.Key.Key_Backspace and not ctrl and self._eat_indent():
            return
        if key == Qt.Key.Key_Home and not ctrl:
            self._smart_home(shift)
            return
        self._typing = bool(event.text()) and event.text().isprintable() and not ctrl
        super().keyPressEvent(event)

    def _on_tab(self) -> None:
        cursor = self.textCursor()
        if cursor.hasSelection() and "\u2029" in cursor.selectedText():
            self.indent()
            return
        before = cursor.block().text()[:cursor.positionInBlock()]
        if before.strip() and TAB_TRIGGER.search(before):
            self.open_completion(True)
            return
        cursor.insertText(INDENT)

    def _on_return(self) -> None:
        cursor = self.textCursor()
        line = cursor.block().text()[:cursor.positionInBlock()]
        indent = line[:len(line) - len(line.lstrip())]
        stripped = line.rstrip()
        if stripped.endswith(":") and not stripped.lstrip().startswith("#"):
            indent += INDENT
        elif re.match(r"\s*(return|pass|break|continue|raise)\b", stripped) and len(indent) >= len(INDENT):
            indent = indent[:-len(INDENT)]
        cursor.insertText("\n" + indent)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def _eat_indent(self) -> bool:
        cursor = self.textCursor()
        if cursor.hasSelection():
            return False
        before = cursor.block().text()[:cursor.positionInBlock()]
        if before and not before.strip() and len(before) % len(INDENT) == 0:
            cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor, len(INDENT))
            cursor.removeSelectedText()
            return True
        return False

    def _smart_home(self, keep_anchor: bool) -> None:
        cursor = self.textCursor()
        text = cursor.block().text()
        first = len(text) - len(text.lstrip())
        column = cursor.positionInBlock()
        target = cursor.block().position() + (0 if column == first else first)
        cursor.setPosition(target, QTextCursor.MoveMode.KeepAnchor if keep_anchor else QTextCursor.MoveMode.MoveAnchor)
        self.setTextCursor(cursor)

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


__all__ = ["CodeEditor", "PythonHighlighter", "CompletionPopup", "badge_pixmap", "item_doc_html"]
