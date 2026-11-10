"""The Script Editor's console: a `>>>` line under the output panel that runs what you type against the fractal.

`ConsoleLine` is a one-line `CodeEditor` (syntax colours and `Tab` completion included): **Enter** runs the line,
**Shift+Enter** adds a line (small blocks such as `for t in transforms: …`), **↑ / ↓** walk the history (kept between
sessions), **Esc** clears. The window runs each line as a script (`ScriptEditorWindow.run_console`): an expression
echoes its value, plain variables carry over to the next line, and a line that changes the fractal is one undo step
("Console: camera.zoom += 1") — one that only looks changes nothing. While Record is on the line is written into the
script as typed.

`console_code(line, variables)` is the Qt-free part: the code actually run for a line (the carried variables assigned
first, a final expression captured for echoing) and how many lines that prefix adds, so errors point at the line typed.
"""

from __future__ import annotations

import ast
import json

from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from ..scripting import completion as C
from ..widgets.code_editor import CodeEditor

HISTORY_KEY = "script/console_history"
HISTORY_SIZE = 100
RESULT_NAME = "__console_value__"


def console_code(line: str, variables: dict) -> tuple[str, int]:
    """The script run for a console `line`: the carried `variables` assigned first, a trailing expression stored in
    `__console_value__` and printed with `repr` (as the Python prompt does). Returns (code, prefix line count)."""
    prefix = "".join(f"{name} = {value!r}\n" for name, value in variables.items())
    try:
        tree = ast.parse(line)
    except SyntaxError:
        return prefix + line, prefix.count("\n")
    if tree.body and isinstance(tree.body[-1], ast.Expr):
        last = tree.body[-1]
        lines = line.split("\n")
        head = "\n".join(lines[:last.lineno - 1])
        expression = "\n".join(lines[last.lineno - 1:last.end_lineno])
        body = (head + "\n" if head else "") + f"{RESULT_NAME} = ({expression})\nif {RESULT_NAME} is not None:\n    print(repr({RESULT_NAME}))\n"
        return prefix + body, prefix.count("\n")
    return prefix + line, prefix.count("\n")


class ConsoleLine(CodeEditor):
    """The console's input (see the module docstring).

    Signals:
        submitted(str): Enter on a non-empty line.
    """
    submitted = Signal(str)

    def __init__(self, settings: QSettings, parent: QWidget | None = None):
        super().__init__(parent)
        self._settings = settings
        self.variables: dict = {}                       # carried between lines (the completer knows their names)
        self.setPlaceholderText("Type a line of script and press Enter (↑ / ↓: history, Shift+Enter: another line)")
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.completer = self._complete
        self._history: list[str] = self._load_history()
        self._position = len(self._history)
        self._draft = ""
        self.textChanged.connect(self._fit_height)
        self._numbers.hide()
        self._fit_height()

    def line_number_width(self) -> int:
        """No gutter: the prompt sits where line numbers would."""
        return 0

    def _complete(self, code: str, position: int, explicit: bool = False):
        prefix = "".join(f"{name} = {value!r}\n" for name, value in self.variables.items())
        result = C.complete(prefix + code, len(prefix) + position, explicit)
        result.start = max(0, result.start - len(prefix))
        return result

    def _fit_height(self) -> None:
        lines = max(1, min(6, self.blockCount()))
        self.setFixedHeight(self.fontMetrics().lineSpacing() * lines + 10)

    # --- history ----------------------------------------------------------------------------------------------------------
    def _load_history(self) -> list[str]:
        try:
            data = json.loads(self._settings.value(HISTORY_KEY, "[]") or "[]")
            return [str(item) for item in data][-HISTORY_SIZE:]
        except (TypeError, ValueError):
            return []

    @property
    def history(self) -> list[str]:
        return list(self._history)

    def remember(self, line: str) -> None:
        if not self._history or self._history[-1] != line:
            self._history.append(line)
            del self._history[:-HISTORY_SIZE]
            self._settings.setValue(HISTORY_KEY, json.dumps(self._history))
        self._position = len(self._history)
        self._draft = ""

    def _walk(self, step: int) -> None:
        if not self._history:
            return
        if self._position == len(self._history):
            self._draft = self.text()
        self._position = max(0, min(len(self._history), self._position + step))
        self.set_text(self._history[self._position] if self._position < len(self._history) else self._draft)
        self.moveCursor(self.textCursor().MoveOperation.End)

    # --- keys --------------------------------------------------------------------------------------------------------------
    def _handle_key(self, event: QKeyEvent) -> bool:
        key, mods = event.key(), event.modifiers()
        shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not shift and not (mods & Qt.KeyboardModifier.ControlModifier):
            text = self.text().strip("\n")
            if text.strip():
                self.submitted.emit(text)
            return True
        if key == Qt.Key.Key_Up and self.textCursor().blockNumber() == 0:
            self._walk(-1)
            return True
        if key == Qt.Key.Key_Down and self.textCursor().blockNumber() == self.blockCount() - 1:
            self._walk(1)
            return True
        if key == Qt.Key.Key_Escape:
            self.set_text("")
            return True
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and shift:
            self._on_return()
            return True
        return super()._handle_key(event)


class ConsolePanel(QWidget):
    """The `>>>` prompt and the line beside it."""

    def __init__(self, settings: QSettings, parent: QWidget | None = None):
        super().__init__(parent)
        self.prompt = QLabel(">>>", self)
        self.prompt.setAlignment(Qt.AlignmentFlag.AlignTop)
        font = self.prompt.font()
        font.setFamily("monospace")
        self.prompt.setFont(font)
        self.line = ConsoleLine(settings, self)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 2, 2)
        layout.addWidget(self.prompt)
        layout.addWidget(self.line, 1)


__all__ = ["ConsoleLine", "ConsolePanel", "console_code", "RESULT_NAME"]
