"""A plain code editor: a QPlainTextEdit with line numbers, an error mark, find / replace and the usual line edits.

This is the language-independent half of the editors — the Script Editor's Python editor and the Formula
Editor's C-dialect editor build on it. What a language adds (a highlighter, completion, its own
indentation rules) goes into a subclass; the hooks are:

* `comment_prefix` — what `toggle_comment()` puts in front of a line (`#`, `//`);
* `indent_after(line)` — whether Enter after `line` opens a deeper level (`:` in Python, `{` in C);
* `dedent_line(line)` — whether Enter after `line` closes a level (`return` / `pass` in Python);
* `completer` — a `(text, position, explicit) -> Completion` function; when set, **Tab** completes the word before
  the cursor (or opens the list when several names match), **Ctrl+Space** opens it anywhere, and the list opens by
  itself while typing when `auto_complete_trigger(before, prefix)` says so; Enter / Tab accept, Esc closes.

Keys: Tab / Shift+Tab indent or outdent a selection, Backspace eats a level of indentation, Ctrl+/ toggles
comments, Ctrl+D duplicates the line, Ctrl+Shift+K deletes it, Alt+Up / Alt+Down move it, Ctrl+] / Ctrl+[
indent / outdent, Home goes to the first non-blank character first, Ctrl+F / Ctrl+H / Ctrl+G / Ctrl+S are
announced as signals for the window to handle.
"""

from __future__ import annotations

import re
from typing import Callable

from PySide6.QtCore import QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFontDatabase, QKeyEvent, QPainter, QPaintEvent, QResizeEvent, QTextCursor, QTextDocument, QTextFormat
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

from ..scripting.completion import Completion, Item
from .completion_popup import POPUP_ROWS, CompletionPopup

INDENT = "    "
TAB_TRIGGER = re.compile(r"[\w.'\"]$")
Completer = Callable[[str, int, bool], Completion]
LINE_NUMBER_PADDING = 10
ERROR_LINE_COLOR = QColor("#c62828")
NUMBER_COLOR = QColor("#8a8a8a")


class LineNumberArea(QWidget):
    """The gutter on the left of a `BaseCodeEditor`; the editor paints it."""

    def __init__(self, editor: "BaseCodeEditor"):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor.line_number_width(), 0)

    def paintEvent(self, event: QPaintEvent) -> None:
        self._editor.paint_line_numbers(event)


class BaseCodeEditor(QPlainTextEdit):
    """Line-numbered plain-text code editor (see the module docstring for the keys and the language hooks).

    Signals:
        find_requested(bool): Ctrl+F (False) / Ctrl+H (True: replace).
        goto_requested(): Ctrl+G.
        save_requested(bool): Ctrl+S (False) / Ctrl+Shift+S (True: save as).
        status(str): A short note for the status bar.
    """
    find_requested = Signal(bool)
    goto_requested = Signal()
    save_requested = Signal(bool)
    status = Signal(str)
    comment_prefix = "#"

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        font.setPointSize(max(10, font.pointSize()))
        self.setFont(font)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._numbers = LineNumberArea(self)
        self._error_line: int | None = None
        self.completer: Completer | None = None
        self.popup = CompletionPopup(self)
        self._completion: Completion | None = None
        self._typing = False
        self.blockCountChanged.connect(lambda _n: self._update_margins())
        self.updateRequest.connect(self._update_numbers)
        self.cursorPositionChanged.connect(self._on_cursor_moved)
        self.textChanged.connect(self._on_text_changed)
        self._update_margins()
        self._highlight_lines()

    # --- language hooks ------------------------------------------------------------------------------------
    def indent_after(self, line: str) -> bool:
        """Whether Enter at the end of `line` should indent the next line one level deeper."""
        return False

    def dedent_line(self, line: str) -> bool:
        """Whether Enter at the end of `line` should indent the next line one level less."""
        return False

    def auto_complete_trigger(self, before: str, prefix: str) -> bool:
        """Whether typing (`before`: the text up to the cursor, `prefix`: the word being typed) should open the list."""
        return len(prefix) >= 2 and before[-1:].isalnum()

    # --- line numbers ------------------------------------------------------------------------------------
    def line_number_width(self) -> int:
        """The gutter width for the current line count."""
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
        """Paint the gutter: the current line in the text colour, the error line in red, the rest grey."""
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
                    painter.setPen(ERROR_LINE_COLOR)
                elif number == current:
                    painter.setPen(self.palette().text().color())
                else:
                    painter.setPen(NUMBER_COLOR)
                painter.drawText(0, top, width, height, Qt.AlignmentFlag.AlignRight, str(number + 1))
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            number += 1

    # --- state ---------------------------------------------------------------------------------------------
    def text(self) -> str:
        """The whole text."""
        return self.toPlainText()

    def set_text(self, text: str) -> None:
        """Replace the contents (clears the undo history and any error mark)."""
        self.setPlainText(text)
        self.document().clearUndoRedoStacks()
        self.set_error_line(None)
        self.moveCursor(QTextCursor.MoveOperation.Start)

    @property
    def position(self) -> int:
        """The cursor's character offset."""
        return self.textCursor().position()

    def line_column(self) -> tuple[int, int]:
        """The cursor's (line, column), 1-based."""
        cursor = self.textCursor()
        return cursor.blockNumber() + 1, cursor.positionInBlock() + 1

    def goto_line(self, line: int, column: int = 1) -> None:
        """Move the cursor to `line` / `column` (1-based, clamped), centre it and take the focus."""
        block = self.document().findBlockByNumber(max(0, min(self.blockCount() - 1, line - 1)))
        cursor = QTextCursor(block)
        cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, max(0, min(column - 1, block.length() - 1)))
        self.setTextCursor(cursor)
        self.centerCursor()
        self.setFocus()

    def set_error_line(self, line: int | None) -> None:
        """Mark a line (1-based) as the one an error points at; None clears the mark."""
        self._error_line = line
        self._highlight_lines()
        self._numbers.update()

    @property
    def error_line(self) -> int | None:
        """The marked error line, if any."""
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

    def _on_text_changed(self) -> None:
        if self._error_line is not None:
            self.set_error_line(None)
        if self.completer is not None:
            if self.popup.isVisible():
                self._refresh_completion()
            elif self._typing:
                self._maybe_auto_complete()
        self._typing = False

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
        """Indent the selected lines one level."""
        self._map_lines(lambda line: INDENT + line if line.strip() else line)

    def outdent(self) -> None:
        """Outdent the selected lines one level (a lone tab or shorter run of spaces counts as a level)."""
        self._map_lines(lambda line: line[len(INDENT):] if line.startswith(INDENT) else line.lstrip(" ") if line[:1] == " " else line[1:] if line[:1] == "\t" else line)

    def toggle_comment(self) -> None:
        """Comment the selected lines out with `comment_prefix`, or uncomment them if they all are."""
        prefix = self.comment_prefix
        first, last = self._selected_block_range()
        lines = [self.document().findBlockByNumber(n).text() for n in range(first, last + 1)]
        content = [line for line in lines if line.strip()]
        all_commented = bool(content) and all(line.lstrip().startswith(prefix) for line in content)
        if all_commented:
            self._map_lines(lambda line: re.sub(r"^(\s*)" + re.escape(prefix) + r"\s?", r"\1", line, count=1))
        else:
            width = min((len(line) - len(line.lstrip()) for line in content), default=0)
            self._map_lines(lambda line: line[:width] + prefix + " " + line[width:] if line.strip() else line)

    def duplicate_line(self) -> None:
        """Insert a copy of the current line below it."""
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
        """Remove the current line."""
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
        cursor.removeSelectedText()
        cursor.deleteChar() if cursor.atStart() else None
        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def move_line(self, delta: int) -> None:
        """Swap the current line with the one above (`delta` < 0) or below."""
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
        """Replace the characters `start`..`end` by `text`."""
        cursor = self.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(text)
        self.setTextCursor(cursor)

    def selected_text(self) -> str:
        """The selection as plain text (paragraph separators turned into newlines)."""
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
        """How many times `needle` occurs."""
        if not needle:
            return 0
        hay = self.toPlainText()
        return hay.count(needle) if case_sensitive else hay.lower().count(needle.lower())

    def replace_current(self, needle: str, replacement: str, case_sensitive: bool = False) -> bool:
        """Replace the selection if it is a match, then select the next match."""
        selected = self.selected_text()
        if needle and (selected == needle if case_sensitive else selected.lower() == needle.lower()):
            self.textCursor().insertText(replacement)
        return self.find_text(needle, False, case_sensitive)

    def replace_all(self, needle: str, replacement: str, case_sensitive: bool = False) -> int:
        """Replace every match as one undo step; returns how many."""
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
        if self.completer is None:
            return
        result = self.completer(self.toPlainText(), self.position, explicit)
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
        self.popup.show_items(result.items[:200], self._popup_position())

    def _popup_position(self) -> QPoint:
        rect = self.cursorRect()
        return self.viewport().mapToGlobal(QPoint(rect.left() - 20, rect.bottom() + 2))

    def _refresh_completion(self) -> None:
        result = self.completer(self.toPlainText(), self.position, False)
        if not result.items or (self._completion is not None and result.start != self._completion.start and not result.in_string):
            self.close_completion()
            if result.items:
                self.open_completion(False)
            return
        self._completion = result
        self.popup.show_items(result.items[:200], self._popup_position())

    def _maybe_auto_complete(self) -> None:
        text = self.toPlainText()
        pos = self.position
        before = text[max(0, pos - 60):pos]
        m = re.search(r"(\w*)$", before)
        if self.auto_complete_trigger(before, m.group(1) if m else ""):
            self.open_completion(False)

    def accept_completion(self) -> None:
        """Insert the candidate selected in the popup."""
        item = self.popup.current()
        if item is None or self._completion is None:
            self.close_completion()
            return
        self._insert_item(item)

    def _insert_item(self, item: Item) -> None:
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

    def _popup_key(self, event: QKeyEvent) -> bool:
        """Keys that drive the visible popup; True when consumed."""
        key = event.key()
        if key in (Qt.Key.Key_Down, Qt.Key.Key_Up, Qt.Key.Key_PageDown, Qt.Key.Key_PageUp):
            self.popup.move_selection({Qt.Key.Key_Down: 1, Qt.Key.Key_Up: -1, Qt.Key.Key_PageDown: POPUP_ROWS, Qt.Key.Key_PageUp: -POPUP_ROWS}[key])
            return True
        if key == Qt.Key.Key_Escape:
            self.close_completion()
            return True
        if key == Qt.Key.Key_Tab:
            self.accept_completion()
            return True
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            item = self.popup.current()
            if item is not None and self._completion is not None and item.text != self._completion.prefix:
                self.accept_completion()
                return True
            self.close_completion()
        if key in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Home, Qt.Key.Key_End):
            self.close_completion()
        return False

    # --- keys ------------------------------------------------------------------------------------------------------
    def keyPressEvent(self, event: QKeyEvent) -> None:
        key, mods = event.key(), event.modifiers()
        ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
        if self.popup.isVisible() and self._popup_key(event):
            return
        if ctrl and key == Qt.Key.Key_Space and self.completer is not None:
            self.open_completion(True)
            return
        if self._handle_key(event):
            return
        self._typing = bool(event.text()) and event.text().isprintable() and not ctrl   # printable keys may open the popup
        super().keyPressEvent(event)

    def _handle_key(self, event: QKeyEvent) -> bool:
        """The editor's own key bindings; True when the event was consumed."""
        key, mods = event.key(), event.modifiers()
        ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
        shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)
        alt = bool(mods & Qt.KeyboardModifier.AltModifier)
        if ctrl and key == Qt.Key.Key_Slash:
            self.toggle_comment()
        elif ctrl and key == Qt.Key.Key_D:
            self.duplicate_line()
        elif ctrl and shift and key == Qt.Key.Key_K:
            self.delete_line()
        elif ctrl and key == Qt.Key.Key_BracketRight:
            self.indent()
        elif ctrl and key == Qt.Key.Key_BracketLeft:
            self.outdent()
        elif alt and key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            self.move_line(-1 if key == Qt.Key.Key_Up else 1)
        elif ctrl and key == Qt.Key.Key_F:
            self.find_requested.emit(False)
        elif ctrl and key == Qt.Key.Key_H:
            self.find_requested.emit(True)
        elif ctrl and key == Qt.Key.Key_G:
            self.goto_requested.emit()
        elif ctrl and key == Qt.Key.Key_S:
            self.save_requested.emit(shift)
        elif key == Qt.Key.Key_Tab and not ctrl:
            self._on_tab()
        elif key == Qt.Key.Key_Backtab:
            self.outdent()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not ctrl:
            self._on_return()
        elif key == Qt.Key.Key_Backspace and not ctrl and self._eat_indent():
            pass
        elif key == Qt.Key.Key_Home and not ctrl:
            self._smart_home(shift)
        else:
            return False
        return True

    def _on_tab(self) -> None:
        """Tab: indent a multi-line selection; complete the word before the cursor when there is a completer; else indent."""
        cursor = self.textCursor()
        if cursor.hasSelection() and "\u2029" in cursor.selectedText():
            self.indent()
            return
        before = cursor.block().text()[:cursor.positionInBlock()]
        if self.completer is not None and before.strip() and TAB_TRIGGER.search(before):
            self.open_completion(True)
            return
        cursor.insertText(INDENT)

    def _on_return(self) -> None:
        """Enter: a new line at the current indentation, one level deeper or shallower as the language hooks say."""
        cursor = self.textCursor()
        line = cursor.block().text()[:cursor.positionInBlock()]
        indent = line[:len(line) - len(line.lstrip())]
        stripped = line.rstrip()
        if self.indent_after(stripped):
            indent += INDENT
        elif self.dedent_line(stripped) and len(indent) >= len(INDENT):
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


__all__ = ["BaseCodeEditor", "LineNumberArea", "INDENT", "Completer"]
