"""*Record*: edits made anywhere in Fractalchemy written into the Script Editor as the code that reproduces them.

`ScriptRecorder` listens to `FractalDocument.edited(kind)` — one announcement per change, from the viewport, the
Inspector, the Gradient Library, the Transform Editor, Paste Parameters, Mutate & Breed … — and asks
`scripting.diff.flame_diff` for the statements that turn the flame as it was into the flame as it is. It never edits
the fractal.

* **Blocks.** The text written for a run of same-kind edits is one *block*, tracked by a `QTextCursor` selection (Qt
  keeps it in place as text changes elsewhere) with the flame from before the first of those edits. While edits of the
  same kind keep coming (a slider drag, a camera drag), the block is rewritten — at most every
  `config.SCRIPT_RECORD_REFRESH_MS` — so a drag ends as one statement. A different kind, typing in the editor or moving
  its cursor closes the block. A block whose diff is empty (the value went back) disappears.
* **Undo-aware.** Undo in the main window that restores exactly what the last block started from removes that block
  (Redo brings it back); other undos and redos are recorded like any edit.
* **Where.** At the editor's cursor, on a line of its own, indented like the cursor's line, without taking the focus
  (you are working in another window); each block is one step of the editor's own undo.
* **Not recorded.** A script's result (the `script` kind — Run stops recording anyway), choosing another fractal (a
  comment says so, and recording carries on from the new one), the image size and the preview settings (not part of
  the fractal).
* **Style.** `absolute` (values: `camera.zoom = 1.25`) or `relative` (changes: `camera.zoom += 0.25`, so a recording
  works as a filter on any fractal; the Gradient Library's own operations are passed along as hints).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QTextCursor

from .. import config
from ..fractal.scene import Flame
from ..model import Gradient
from ..scripting.codegen import flames_equivalent
from ..scripting.diff import flame_diff
from ..widgets.code_editor import CodeEditor
from .fractal_document import FractalDocument

ABSOLUTE, RELATIVE = "absolute", "relative"
UNDO_STACK = 50
IGNORED_KINDS = frozenset({"script"})


@dataclass
class Block:
    """Text the recorder wrote for one run of same-kind edits."""
    kind: str
    base: Flame                 # the flame before the first edit of the run
    cursor: QTextCursor         # selects the block's text (including the line break in front of it)
    text: str = ""
    after: Flame | None = None  # the flame the block's statements lead to (undo-aware removal / redo)
    target: Flame | None = None  # the flame after the latest same-kind edit (what a pending rewrite writes towards)


class ScriptRecorder(QObject):
    """The recorder (see the module docstring).

    Signals:
        recording_changed(bool): Started or stopped.
    """
    recording_changed = Signal(bool)

    def __init__(self, document: FractalDocument, editor: CodeEditor, gradient_hint: Callable[[], Gradient | None] | None = None,
                 parent: QObject | None = None):
        super().__init__(parent)
        self.document = document
        self.editor = editor
        self.gradient_hint = gradient_hint or (lambda: None)
        self.style = ABSOLUTE
        self._recording = False
        self._baseline: Flame | None = None
        self._block: Block | None = None
        self._blocks: list[Block] = []               # recent intact blocks, newest last (undo-aware removal)
        self._redo: list[Block] = []
        self._writing = False
        self._dirty = False
        self._timer = QTimer(self, singleShot=True, interval=config.SCRIPT_RECORD_REFRESH_MS)
        self._timer.timeout.connect(self._refresh)

    # --- on / off --------------------------------------------------------------------------------------------------------
    @property
    def recording(self) -> bool:
        return self._recording

    def start(self, style: str | None = None) -> bool:
        """Start recording (False without a fractal to record)."""
        if self._recording:
            return True
        if self.document.flame is None:
            return False
        if style is not None:
            self.style = style
        self._baseline = self.document.flame.copy()
        self._block, self._blocks, self._redo = None, [], []
        self.document.edited.connect(self._on_edited)
        self.editor.document().contentsChange.connect(self._on_text_edited)
        self.editor.cursorPositionChanged.connect(self._on_cursor_moved)
        self._recording = True
        self.recording_changed.emit(True)
        return True

    def stop(self) -> None:
        """Stop recording (what is pending is written first)."""
        if not self._recording:
            return
        self._flush()
        self.document.edited.disconnect(self._on_edited)
        self.editor.document().contentsChange.disconnect(self._on_text_edited)
        self.editor.cursorPositionChanged.disconnect(self._on_cursor_moved)
        self._recording = False
        self._block = None
        self.recording_changed.emit(False)

    # --- edits -------------------------------------------------------------------------------------------------------------
    def _on_edited(self, kind: str) -> None:
        flame = self.document.flame
        if flame is None:
            return
        if kind in IGNORED_KINDS:
            self._close()
            self._baseline = flame.copy()
            return
        if kind == "load":
            self._close()
            self._write_lines([f"# (switched to '{flame.name}' — not recorded)"], None)
            self._baseline = flame.copy()
            return
        if kind == "undo" and self._undo_last_block(flame):
            return
        if kind == "redo" and self._redo_block(flame):
            return
        if self._block is not None and self._block.kind == kind and self._intact(self._block):
            self._block.target = flame.copy()
            self._dirty = True
            if not self._timer.isActive():
                self._timer.start()
        else:
            self._close()
            base = self._baseline if self._baseline is not None else flame
            self._block = self._new_block(kind, base)
            self._block.target = flame.copy()
            self._dirty = True
            self._refresh()
        self._baseline = flame.copy()

    def _lines(self, block: Block) -> list[str]:
        flame = block.target if block.target is not None else self.document.flame
        gradient = self.gradient_hint() if block.kind == "palette" else None
        hints = self.document.last_edit_hint if self.style == RELATIVE and block.kind == "palette" else None
        return flame_diff(block.base, flame, gradient, self.style, hints)

    def _refresh(self) -> None:
        """Rewrite the open block from its base to the flame as it is now."""
        self._timer.stop()
        block = self._block
        if block is None or not self._dirty:
            return
        self._dirty = False
        lines = self._lines(block)
        self._replace(block, lines)
        block.after = block.target
        if not lines:
            self._forget(block)

    def _flush(self) -> None:
        if self._dirty:
            self._refresh()

    def _close(self) -> None:
        """Finish the open block (a different kind of edit, typing, or stopping)."""
        self._flush()
        self._block = None

    def _new_block(self, kind: str, base: Flame) -> Block:
        cursor = QTextCursor(self.editor.document())
        cursor.setPosition(self.editor.textCursor().position())
        block = Block(kind, base.copy(), cursor)
        self._blocks.append(block)
        del self._blocks[:-UNDO_STACK]
        self._redo.clear()
        return block

    def _forget(self, block: Block) -> None:
        if block in self._blocks:
            self._blocks.remove(block)
        if self._block is block:
            self._block = None

    # --- writing ---------------------------------------------------------------------------------------------------------
    def _indent(self, cursor: QTextCursor) -> str:
        line = cursor.block().text()
        return line[:len(line) - len(line.lstrip())]

    def _format(self, lines: list[str], cursor: QTextCursor) -> str:
        """The text for `lines` at `cursor`: on a line of its own, indented like that line."""
        if not lines:
            return ""
        indent = self._indent(cursor)
        line = cursor.block().text()
        before = line[:cursor.positionInBlock()]
        body = ("\n" + indent).join(lines)
        return ("\n" + indent if before.strip() else "") + body

    def _replace(self, block: Block, lines: list[str]) -> None:
        """Put `lines` where the block is (inserting it the first time), as one editor undo step."""
        cursor = block.cursor
        fresh = not block.text
        start = cursor.selectionStart()
        if fresh:                                               # a new block goes after the cursor's line
            cursor.setPosition(start)
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
            start = cursor.position()
        text = self._format(lines, cursor) if fresh else (self._continuation(block, lines))
        self._writing = True
        try:
            if fresh:
                cursor.beginEditBlock()
            else:
                cursor.joinPreviousEditBlock()
            cursor.insertText(text)
            cursor.endEditBlock()
            end = cursor.position()
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            block.text = text
            mover = self.editor.textCursor()
            mover.setPosition(end)
            self.editor.setTextCursor(mover)
            self.editor.ensureCursorVisible()
        finally:
            self._writing = False

    def _continuation(self, block: Block, lines: list[str]) -> str:
        """New text for an existing block, keeping the line break / indentation it started with."""
        old = block.text
        indent = ""
        lead = ""
        if old.startswith("\n"):
            rest = old[1:]
            indent = rest[:len(rest) - len(rest.lstrip(" \t"))]
            lead = "\n" + indent
        else:
            doc_block = self.editor.document().findBlock(block.cursor.selectionStart())
            text = doc_block.text()
            indent = text[:len(text) - len(text.lstrip(" \t"))]
        return (lead + ("\n" + indent).join(lines)) if lines else ""

    def _write_lines(self, lines: list[str], kind: str | None) -> None:
        """Write lines that are not a diff (a comment, a console line) as a closed block of their own."""
        block = self._new_block(kind or "note", self.document.flame or Flame())
        self._replace(block, lines)
        self._forget(block)

    def insert_code(self, code: str) -> None:
        """A console line typed while recording: written as typed (it already is code)."""
        if self._recording:
            self._close()
            self._write_lines(code.split("\n"), "console")

    def _intact(self, block: Block) -> bool:
        """The block's text is still exactly what the recorder wrote."""
        return block.cursor.selectedText().replace("\u2029", "\n") == block.text

    # --- undo / redo in the main window ---------------------------------------------------------------------------------------
    def _undo_last_block(self, flame: Flame) -> bool:
        """Undo restored what the newest block started from: remove the block (Redo can bring it back)."""
        self._flush()
        if not self._blocks:
            return False
        block = self._blocks[-1]
        if not block.text or not self._intact(block) or not flames_equivalent(flame, block.base):
            return False
        position = block.cursor.selectionStart()
        self._writing = True
        try:
            block.cursor.beginEditBlock()
            block.cursor.removeSelectedText()
            block.cursor.endEditBlock()
        finally:
            self._writing = False
        self._blocks.pop()
        self._redo.append(Block(block.kind, block.base, QTextCursor(self.editor.document()), block.text, block.after))
        self._redo[-1].cursor.setPosition(min(position, self.editor.document().characterCount() - 1))
        self._block = None
        self._baseline = flame.copy()
        return True

    def _redo_block(self, flame: Flame) -> bool:
        """Redo brought back what a removed block led to: put its text back where it was."""
        if not self._redo or self._redo[-1].after is None or not flames_equivalent(flame, self._redo[-1].after):
            return False
        block = self._redo.pop()
        start = block.cursor.position()
        self._writing = True
        try:
            block.cursor.beginEditBlock()
            block.cursor.insertText(block.text)
            block.cursor.endEditBlock()
            end = block.cursor.position()
            block.cursor.setPosition(start)
            block.cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        finally:
            self._writing = False
        self._blocks.append(block)
        self._block = None
        self._baseline = flame.copy()
        return True

    # --- the user in the editor ------------------------------------------------------------------------------------------
    def _on_text_edited(self, _position: int, removed: int, added: int) -> None:
        if not self._writing and (removed or added) and removed != added:   # equal counts: a formatting-only change
            self._close()

    def _on_cursor_moved(self) -> None:
        if self._writing or self._block is None:
            return
        if self.editor.textCursor().position() != self._block.cursor.selectionEnd():
            self._close()


__all__ = ["ScriptRecorder", "ABSOLUTE", "RELATIVE"]
