"""The Script Editor's output panel: `print` text, notes in the theme's colours, and errors that jump to their line."""

from __future__ import annotations

from html import escape

from PySide6.QtCore import Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QTextBrowser, QWidget

from ..widgets.theming import current_theme

MAX_OUTPUT_BLOCKS = 3000


class OutputPanel(QTextBrowser):
    """The script's output: `print` text, results, and errors that jump to their line when clicked.

    Signals:
        line_clicked(int): An error line was clicked.
    """
    line_clicked = Signal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setOpenLinks(False)
        self.setPlaceholderText("print() output, results and errors appear here")
        self.document().setMaximumBlockCount(MAX_OUTPUT_BLOCKS)
        self.anchorClicked.connect(lambda url: self.line_clicked.emit(int(url.toString().split(":")[1])))
        font = self.font()
        font.setFamily("monospace")
        self.setFont(font)
        self._pending = ""
        self._live_start: int | None = None     # first block of the live-parameter section (see replace_live_section)

    def append_text(self, text: str) -> None:
        """Plain text from print (may contain several lines, may lack a final newline)."""
        self._pending += text
        while "\n" in self._pending:
            line, self._pending = self._pending.split("\n", 1)
            self._append_html(escape(line) or " ")

    def flush(self) -> None:
        if self._pending:
            self._append_html(escape(self._pending))
            self._pending = ""

    def _append_html(self, html: str) -> None:
        self.append(f"<span style='white-space: pre'>{html}</span>")

    def append_note(self, text: str, kind: str = "info", line: int | None = None) -> None:
        """A coloured line in the theme's colours: `info` (dimmed), `ok` (success), `error` (clickable when `line` is given)."""
        self.flush()
        color = current_theme()[{"info": "dim_text", "ok": "success", "error": "error"}.get(kind, "text")]
        body = escape(text).replace("\n", "<br>")
        if line is not None:
            body = f"<a href='line:{line}' style='color: {color}'>{body}</a>"
        self._append_html(f"<span style='color: {color}'>{body}</span>")

    def clear_output(self) -> None:
        self._pending = ""
        self._live_start = None
        self.clear()

    # --- the live section: what the latest live-parameter re-run printed, replaced by the next one -----------------------
    def replace_live_section(self, text: str, note: str, kind: str = "info", line: int | None = None) -> None:
        """Replace what the previous re-run wrote (or start the section) by `text` (its prints) and a `note`."""
        self.flush()
        doc = self.document()
        if self._live_start is None:
            self._live_start = 0 if doc.isEmpty() else doc.blockCount()
        if self._live_start < doc.blockCount() and not doc.isEmpty():
            start = doc.findBlockByNumber(self._live_start)
            cursor = QTextCursor(doc)
            cursor.setPosition(max(0, start.position() - 1) if self._live_start else 0)
            cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
        for piece in text.rstrip("\n").split("\n") if text.strip() else []:
            self._append_html(escape(piece) or " ")
        self.append_note(note, kind, line)

    def end_live_section(self) -> None:
        """The next output is ordinary output again (a full run started)."""
        self._live_start = None


__all__ = ["OutputPanel", "MAX_OUTPUT_BLOCKS"]
