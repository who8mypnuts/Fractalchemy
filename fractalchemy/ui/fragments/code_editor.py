"""The fragment source editor: `BaseCodeEditor` with GLSL highlighting, bracket matching and a completer.

The highlighter knows GLSL's keywords, types, built-in functions and variables, the preprocessor directives
(Fragmentarium's `#include` / `#preset` / `#group` / … among them), the uniform annotations (`slider[…]`, `color[…]`,
`checkbox[…]`, `menu[…]`, `file[…]` and the lock words) in their own colour, strings, numbers and both comment
styles; `#preset` blocks are dimmed so the code stands out. Completion (Tab / Ctrl+Space, or by itself after two
letters) offers GLSL's built-ins, the directives, the special uniforms and every identifier the document already
uses. Enter after `{` indents; `}` on a blank indented line outdents; Ctrl+/ comments with `//`.
"""

from __future__ import annotations

import re

from PySide6.QtGui import QColor, QFont, QKeyEvent, QSyntaxHighlighter, QTextCharFormat, QTextCursor, QTextDocument
from PySide6.QtWidgets import QTextEdit, QWidget

from ...fragments import glsl_keywords as K
from ...scripting.completion import Completion, Item
from ...widgets.base_code_editor import INDENT, BaseCodeEditor

COLORS = {"keyword": "#7b2fa0", "type": "#1565c0", "function": "#3b5f9e", "builtin": "#8d5a00", "string": "#2e7d32",
          "comment": "#8a8a8a", "number": "#c45200", "preprocessor": "#4a7a48", "annotation": "#b5541c", "preset": "#9a9a9a",
          "special": "#0d47a1"}
BLOCK_COMMENT, IN_PRESET = 1, 2
BRACKETS = {"(": ")", "[": "]", "{": "}"}
CLOSERS = {v: k for k, v in BRACKETS.items()}
WORD = re.compile(r"[A-Za-z_]\w*")
FUNCTION_DEF = re.compile(r"^[ \t]*((?:[a-z]+\s+)?(?:void|float|int|bool|uint|double|[biud]?vec[234]|mat[234](?:x[234])?|d?mat[234]))\s+([A-Za-z_]\w*)\s*\(([^)]*)\)\s*\{", re.MULTILINE)
NUMBER = re.compile(r"\b(?:0[xX][0-9A-Fa-f]+[uU]?|\d+\.?\d*(?:[eE][+-]?\d+)?[fFuUlL]{0,2}|\.\d+(?:[eE][+-]?\d+)?[fF]?)\b")
ANNOTATION = re.compile(r"\b(slider|color|checkbox|menu|file)\s*\[[^\]]*\]|\b(Locked|NotLocked|NotLockable|AlwaysLocked|Logarithmic)\b")
MATCH_COLOR = QColor(30, 136, 229, 70)


class GlslHighlighter(QSyntaxHighlighter):
    """Colouring for fragment sources (see the module docstring)."""

    def __init__(self, document: QTextDocument):
        super().__init__(document)
        self._formats = {name: self._format(colour, bold=name in ("keyword", "preprocessor")) for name, colour in COLORS.items()}
        self._formats["comment"].setFontItalic(True)
        self._formats["preset"].setFontItalic(True)

    @staticmethod
    def _format(colour: str, bold: bool = False) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(colour))
        if bold:
            fmt.setFontWeight(QFont.Weight.Bold)
        return fmt

    def highlightBlock(self, text: str) -> None:  # noqa: N802 - Qt override
        previous = self.previousBlockState()
        self.setCurrentBlockState(0)
        stripped = text.strip().lower()
        if previous == IN_PRESET or stripped.startswith("#preset"):
            self.setFormat(0, len(text), self._formats["preset"])
            self.setCurrentBlockState(0 if stripped.startswith("#endpreset") else IN_PRESET)
            return
        i = 0
        if previous == BLOCK_COMMENT:
            end = text.find("*/")
            if end < 0:
                self.setFormat(0, len(text), self._formats["comment"])
                self.setCurrentBlockState(BLOCK_COMMENT)
                return
            self.setFormat(0, end + 2, self._formats["comment"])
            i = end + 2
        if text.lstrip().startswith("#") and i == 0:
            self._preprocessor_line(text)
            return
        self._code(text, i)

    def _preprocessor_line(self, text: str) -> None:
        self.setFormat(0, len(text), self._formats["preprocessor"])
        for m in re.finditer(r'"[^"]*"', text):
            self.setFormat(m.start(), m.end() - m.start(), self._formats["string"])
        comment = text.find("//")
        if comment >= 0:
            self.setFormat(comment, len(text) - comment, self._formats["comment"])

    def _code(self, text: str, start: int) -> None:
        """Code from `start`: comments end or suspend the scan; the rest is words, numbers, annotations."""
        i = start
        n = len(text)
        segment_start = i
        while i < n:
            two = text[i:i + 2]
            if two == "//":
                self._words(text, segment_start, i)
                self.setFormat(i, n - i, self._formats["comment"])
                return
            if two == "/*":
                self._words(text, segment_start, i)
                end = text.find("*/", i + 2)
                if end < 0:
                    self.setFormat(i, n - i, self._formats["comment"])
                    self.setCurrentBlockState(BLOCK_COMMENT)
                    return
                self.setFormat(i, end + 2 - i, self._formats["comment"])
                i = segment_start = end + 2
                continue
            i += 1
        self._words(text, segment_start, n)

    def _words(self, text: str, start: int, end: int) -> None:
        segment = text[start:end]
        for m in NUMBER.finditer(segment):
            self.setFormat(start + m.start(), m.end() - m.start(), self._formats["number"])
        for m in WORD.finditer(segment):
            word = m.group(0)
            fmt = ("keyword" if word in K.KEYWORDS else "type" if word in K.TYPES else "function" if word in K.FUNCTIONS
                   else "builtin" if word in K.BUILTIN_VARIABLES else "special" if word in K.SPECIAL_UNIFORMS else None)
            if fmt:
                self.setFormat(start + m.start(), len(word), self._formats[fmt])
        for m in ANNOTATION.finditer(segment):
            self.setFormat(start + m.start(), m.end() - m.start(), self._formats["annotation"])


def complete(text: str, position: int, explicit: bool, extra_words: tuple[str, ...] = ()) -> Completion:
    """Completion candidates at `position`: GLSL built-ins, directives, the fragment's own identifiers."""
    before = text[:position]
    m = re.search(r"(#?[A-Za-z_]\w*)$", before)
    prefix = m.group(1) if m else ""
    start = position - len(prefix)
    if not prefix and not explicit:
        return Completion([], prefix, start)
    candidates: list[Item] = []
    if prefix.startswith("#"):
        pool = [(d, "keyword", "directive") for d in K.DIRECTIVES]
    else:
        functions = own_functions(text)
        own = sorted(set(WORD.findall(text)) - {prefix} - K.KEYWORDS - K.TYPES - K.FUNCTIONS - set(extra_words) - set(functions))
        pool = ([(w, "function", "GLSL") for w in sorted(K.FUNCTIONS)] + [(w, "class", "type") for w in sorted(K.TYPES)]
                + [(w, "keyword", "") for w in sorted(K.KEYWORDS)] + [(w, "variable", "built-in") for w in sorted(K.BUILTIN_VARIABLES)]
                + [(w, "variable", "special uniform") for w in K.SPECIAL_UNIFORMS] + [(w, "constant", "define") for w in K.FRAGMENTARIUM_DEFINES]
                + [(w, "keyword", "annotation") for w in K.ANNOTATIONS]
                + [(w, "function", "in this fragment") for w in sorted(functions)]
                + [(w, "variable", "in this fragment") for w in own] + [(w, "variable", "") for w in extra_words])
    lowered = prefix.lower()
    seen: set[str] = set()
    for name, kind, detail in pool:
        if name.lower().startswith(lowered) and name != prefix and name not in seen:
            seen.add(name)
            candidates.append(_item(name, kind, detail, text))
    candidates.sort(key=lambda item: not item.name.startswith(prefix))     # exact-case matches first, pool order otherwise
    return Completion(candidates, prefix, start)


def _item(name: str, kind: str, detail: str, text: str) -> Item:
    """A candidate with its one-line documentation (GLSL built-ins, the host's words) or its own signature."""
    doc = K.DOCS.get(name)
    if doc is not None:
        return Item(name, kind, sig=doc[0], desc=doc[1])
    if detail == "in this fragment" and kind == "function":
        return Item(name, kind, sig=own_functions(text).get(name, ""), desc="defined in this fragment")
    return Item(name, kind, desc=detail)


def own_functions(text: str) -> dict[str, str]:
    """`name → signature` of the functions the text defines (`float DE(vec3 p) {`)."""
    return {m.group(2): f"{m.group(1)} {m.group(2)}({' '.join(m.group(3).split())})" for m in FUNCTION_DEF.finditer(text)}


class GlslCodeEditor(BaseCodeEditor):
    """Editor for fragment sources (see the module docstring)."""
    comment_prefix = "//"

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setPlaceholderText("// Write fragment code here, or open an example from the library…")
        self.highlighter = GlslHighlighter(self.document())
        self.completer = lambda text, pos, explicit: complete(text, pos, explicit)
        self.cursorPositionChanged.connect(self._match_brackets)
        self._bracket_selections: list = []

    def indent_after(self, line: str) -> bool:
        return line.rstrip().endswith("{")

    def auto_complete_trigger(self, before: str, prefix: str) -> bool:
        return len(prefix) >= 2 and not before.rstrip().endswith(("//",))

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.text() == "}" and self._close_brace():
            return
        super().keyPressEvent(event)

    def _close_brace(self) -> bool:
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
        return True

    # --- bracket matching ----------------------------------------------------------------------------------------------
    def _match_brackets(self) -> None:
        text = self.toPlainText()
        pos = self.position
        pair = None
        for at in (pos - 1, pos):
            if 0 <= at < len(text) and text[at] in BRACKETS:
                pair = (at, self._find_match(text, at, 1))
                break
            if 0 <= at < len(text) and text[at] in CLOSERS:
                pair = (at, self._find_match(text, at, -1))
                break
        selections = []
        if pair and pair[1] is not None:
            for at in pair:
                selection = QTextEdit.ExtraSelection()
                selection.format.setBackground(MATCH_COLOR)
                selection.cursor = QTextCursor(self.document())
                selection.cursor.setPosition(at)
                selection.cursor.setPosition(at + 1, QTextCursor.MoveMode.KeepAnchor)
                selections.append(selection)
        self._bracket_selections = selections
        self._highlight_lines()

    @staticmethod
    def _find_match(text: str, at: int, direction: int) -> int | None:
        opener = text[at] if direction > 0 else CLOSERS[text[at]]
        closer = BRACKETS[opener]
        depth = 0
        i = at
        while 0 <= i < len(text):
            if text[i] == opener:
                depth += 1
            elif text[i] == closer:
                depth -= 1
            if depth == 0:
                return i
            i += direction
        return None

    def _highlight_lines(self) -> None:
        super()._highlight_lines()
        brackets = getattr(self, "_bracket_selections", [])      # the base class highlights during its own __init__
        if brackets:
            self.setExtraSelections(list(self.extraSelections()) + brackets)

    # --- FragM's indenter -------------------------------------------------------------------------------------------------
    def indent_script(self) -> None:
        """FragM's *Indent script*: every line indented by its brace / parenthesis depth (tabs)."""
        lines = self.toPlainText().split("\n")
        out, depth = [], 0
        for line in lines:
            stripped = line.strip()
            offset = -1 if stripped.startswith("}") else 0
            out.append("\t" * max(0, depth + offset) + stripped)
            depth += line.count("{") + line.count("(") - line.count("}") - line.count(")")
        position = self.position
        self.set_text("\n".join(out))
        cursor = self.textCursor()
        cursor.setPosition(min(position, len(self.toPlainText())))
        self.setTextCursor(cursor)

    def select_line_range(self, first: int, last: int) -> None:
        """Select whole lines `first`..`last` (1-based, inclusive) and scroll to them."""
        document = self.document()
        start = document.findBlockByNumber(max(0, first - 1))
        end = document.findBlockByNumber(max(0, last - 1))
        cursor = QTextCursor(start)
        cursor.setPosition(end.position() + end.length() - 1, QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(cursor)
        self.centerCursor()


__all__ = ["GlslCodeEditor", "GlslHighlighter", "complete"]
