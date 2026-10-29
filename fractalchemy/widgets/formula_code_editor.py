"""The Formula Editor's code editor: `BaseCodeEditor` with highlighting for the Apophysis plugin C dialect.

The highlighter knows the language the compiler knows (`formulas/lang/builtins.py`): C keywords and types,
the plugin API (`APO_PLUGIN`, `APO_VARIABLES`, `VAR_REAL` …, `VAR()`, `TM()`), the point state
(`FTx`, `FPy`, `TC`, `VVAR`), the math functions and constants, preprocessor lines, strings, numbers and
both comment styles (`/* … */` spanning lines through the block state).

Indentation: Enter after `{` opens a level; typing `}` on a blank indented line closes one.
"""

from __future__ import annotations

import re

from PySide6.QtGui import QColor, QFont, QKeyEvent, QSyntaxHighlighter, QTextCharFormat, QTextCursor, QTextDocument
from PySide6.QtWidgets import QWidget

from ..formulas.lang import builtins as B
from .base_code_editor import INDENT, BaseCodeEditor

COLORS = {
    "keyword": "#7b2fa0", "type": "#1565c0", "api": "#0d47a1", "state": "#8d5a00", "function": "#3b5f9e", "constant": "#7a3a3a",
    "string": "#2e7d32", "comment": "#8a8a8a", "number": "#c45200", "preprocessor": "#4a7a48",
}
KEYWORDS = {"if", "else", "for", "while", "do", "switch", "case", "default", "break", "continue", "return", "goto", "typedef",
            "struct", "static", "const", "inline", "sizeof", "extern", "volatile", "register", "enum", "union"}
TYPES = {"double", "float", "int", "bool", "void", "char", "long", "short", "unsigned", "signed", "Variables", "Variation", "Complex"}
API = {"APO_PLUGIN", "APO_VARIABLES", "APO_NOVARIABLES", "VAR", "TM", "PluginVarPrepare", "PluginVarCalc", "PluginVarGetName",
       "PluginVarGetVariableCount", "PluginVarGetVariableNameAt", "PluginVarGetVariable", "PluginVarSetVariable",
       "PluginVarResetVariable", "vp", "DLLEXPORT", "DLLIMPORT"} | set(B.VARIABLE_MACROS)
STATE = set(B.STATE_NAMES) | {"VVAR"}
FUNCTIONS = set(B.MATH_FUNCTIONS) | set(B.OUT_FUNCTIONS) | {"MAX", "MIN"}
CONSTANTS = set(B.CONSTANTS)
BLOCK_COMMENT = 1


class CHighlighter(QSyntaxHighlighter):
    """Colouring for the plugin dialect (see the module docstring)."""

    def __init__(self, document: QTextDocument):
        super().__init__(document)
        self._formats = {name: self._format(color, bold=name in ("keyword", "api")) for name, color in COLORS.items()}
        self._formats["comment"].setFontItalic(True)
        self._word = re.compile(r"[A-Za-z_]\w*")
        self._number = re.compile(r"\b(?:0[xX][0-9A-Fa-f]+|\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)[fFlLuUi]*\b")

    @staticmethod
    def _format(color: str, bold: bool = False) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if bold:
            fmt.setFontWeight(QFont.Weight.Bold)
        return fmt

    def highlightBlock(self, text: str) -> None:
        n = len(text)
        i = 0
        self.setCurrentBlockState(0)
        if self.previousBlockState() == BLOCK_COMMENT:
            end = text.find("*/")
            if end < 0:
                self.setFormat(0, n, self._formats["comment"])
                self.setCurrentBlockState(BLOCK_COMMENT)
                return
            self.setFormat(0, end + 2, self._formats["comment"])
            i = end + 2
        if text.lstrip().startswith("#") and i == 0:
            self.setFormat(0, n, self._formats["preprocessor"])
            self._highlight_strings_only(text)
            return
        code_start = i
        while i < n:
            two = text[i:i + 2]
            if two == "//":
                self._highlight_code(text, code_start, i)
                self.setFormat(i, n - i, self._formats["comment"])
                return
            if two == "/*":
                self._highlight_code(text, code_start, i)
                end = text.find("*/", i + 2)
                if end < 0:
                    self.setFormat(i, n - i, self._formats["comment"])
                    self.setCurrentBlockState(BLOCK_COMMENT)
                    return
                self.setFormat(i, end + 2 - i, self._formats["comment"])
                i = code_start = end + 2
                continue
            if text[i] in "\"'":
                self._highlight_code(text, code_start, i)
                i = code_start = self._string_end(text, i)
                continue
            i += 1
        self._highlight_code(text, code_start, n)

    def _string_end(self, text: str, start: int) -> int:
        """Format the string literal starting at `start`; returns the index after it."""
        quote = text[start]
        j = start + 1
        while j < len(text):
            if text[j] == "\\":
                j += 2
                continue
            if text[j] == quote:
                j += 1
                break
            j += 1
        j = min(j, len(text))
        self.setFormat(start, j - start, self._formats["string"])
        return j

    def _highlight_strings_only(self, text: str) -> None:
        for m in re.finditer(r'"(?:\\.|[^"\\])*"', text):
            self.setFormat(m.start(), m.end() - m.start(), self._formats["string"])

    def _highlight_code(self, text: str, start: int, end: int) -> None:
        segment = text[start:end]
        for m in self._number.finditer(segment):
            self.setFormat(start + m.start(), m.end() - m.start(), self._formats["number"])
        for m in self._word.finditer(segment):
            word = m.group(0)
            fmt = None
            if word in KEYWORDS:
                fmt = "keyword"
            elif word in TYPES:
                fmt = "type"
            elif word in API:
                fmt = "api"
            elif word in STATE:
                fmt = "state"
            elif word in FUNCTIONS:
                fmt = "function"
            elif word in CONSTANTS:
                fmt = "constant"
            if fmt:
                self.setFormat(start + m.start(), len(word), self._formats[fmt])


class FormulaCodeEditor(BaseCodeEditor):
    """Editor for formula sources: C highlighting, `//` comments, brace-aware indentation."""
    comment_prefix = "//"

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setPlaceholderText("// Choose a formula from the list, or click New formula for a template.")
        self.highlighter = CHighlighter(self.document())

    def indent_after(self, line: str) -> bool:
        """A block opener: the line ends with `{`."""
        return line.endswith("{")

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.text() == "}" and self._close_brace():
            return
        super().keyPressEvent(event)

    def _close_brace(self) -> bool:
        """`}` typed on a blank, indented line: outdent the line one level first (and insert the brace)."""
        cursor = self.textCursor()
        if cursor.hasSelection():
            return False
        before = cursor.block().text()[:cursor.positionInBlock()]
        if not before or before.strip() or len(before) < len(INDENT):
            return False
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor, len(INDENT))
        cursor.removeSelectedText()
        cursor.insertText("}")
        cursor.endEditBlock()
        self.setTextCursor(cursor)
        return True


__all__ = ["FormulaCodeEditor", "CHighlighter", "KEYWORDS", "TYPES", "API", "STATE", "FUNCTIONS", "CONSTANTS"]
