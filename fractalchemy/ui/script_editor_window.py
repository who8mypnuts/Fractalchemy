"""The Script Editor window: write and run Python scripts that edit the fractal shown in the main window.

Opened from *Windows ▸ Script Editor* (`F8`) or the toolbar. Like the Gradient Library it is a tool window
of the main window: closing it hides it and the script is kept (and remembered between runs in QSettings).

Layout: a toolbar (New / Open / Save / Save As · Run / Stop · Undo / Redo · Find, Comment, Indent, Outdent ·
Check syntax · Flame → Script · Revert flame · Save as template · Clear output · Drawer), the code editor
with an output panel beneath it on the left, and on the right a sliding drawer (collapsible like the main
window's panels) with four tabs — *Context* (dynamic documentation), *Reference* (guide + API), *Info*
(about this script) and *Templates*.

A script runs on a worker thread against a copy of the flame (`ScriptRunner`); `print` output streams into the
output panel, prompts pop up dialogs, `update()` pushes intermediate results into the main window, and the
result replaces the fractal as one undo step. Errors are reported with their line (click to jump there).
"""

from __future__ import annotations

import re
import time
from html import escape
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QGuiApplication, QKeySequence, QTextCursor
from PySide6.QtWidgets import (
    QFileDialog, QInputDialog, QLabel, QMainWindow, QMessageBox, QProgressBar, QSplitter, QTextBrowser, QToolBar, QVBoxLayout, QWidget,
)

from ..fractal.scene import Flame
from ..scripting import completion as C
from ..scripting import docs as D
from ..scripting import templates as T
from ..scripting.generate import flame_to_script
from ..scripting.runner import ScriptResult, check_syntax
from ..widgets.code_editor import CodeEditor
from ..widgets.collapsible_splitter import CollapsibleSplitter
from ..widgets.find_bar import FindBar
from ..widgets.icons import action_icon, script_icon
from .fractal_document import FractalDocument
from .script_drawer import ScriptDrawer
from .script_runner import REQUEST_CONFIRM, REQUEST_INPUT, ScriptRunner

WINDOW_TITLE = "Script Editor"
DRAWER_WIDTH = 400
OUTPUT_HEIGHT = 150
MAX_OUTPUT_BLOCKS = 3000
RENDER_WAIT_MS = 2500
DRAFT_KEY = "script/draft"
FILE_KEY = "script/file"
NAME_KEY = "script/name"
MODIFIED_KEY = "script/modified"
TAB_KEY = "script/drawer_tab"
DRAWER_KEY = "script/drawer_collapsed"
GEOMETRY_KEY = "script/geometry"
SPLIT_KEY = "script/split"
FOLDER_KEY = "script/folder"
SCRIPT_FILTER = "Python scripts (*.py);;All files (*)"
DEFAULT_SCRIPT = """\
# @name New script
# @description Describe what this script does
#
# Press Ctrl+Enter (or the ▶ button) to run. Type "transform." or "gradient." and press Tab for completion.
# The Context tab on the right follows the cursor and shows what you can use.

for t in transforms:
    t.rotate(random(-30, 30))
print('rotated', len(transforms), 'transforms')
"""


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
        """A coloured line: `info` (grey), `ok` (green), `error` (red, clickable when `line` is given)."""
        self.flush()
        color = {"info": "#777777", "ok": "#2e7d32", "error": "#c62828"}.get(kind, "#333333")
        body = escape(text).replace("\n", "<br>")
        if line is not None:
            body = f"<a href='line:{line}' style='color: {color}'>{body}</a>"
        self._append_html(f"<span style='color: {color}'>{body}</span>")

    def clear_output(self) -> None:
        self._pending = ""
        self.clear()


class ScriptEditorWindow(QMainWindow):
    """The Script Editor tool window, bound to the main window's document."""

    def __init__(self, document: FractalDocument, parent: QWidget | None = None, settings: QSettings | None = None,
                 user_dir: Path | None = None):
        """Args:
            document: The fractal scripts act on.
            parent: Owning window; when given this becomes a child top-level window.
            settings: Where the draft, layout and preferences persist (the application's store by default).
            user_dir: Folder for the user's scripts and templates (default `templates.user_script_dir()`).
        """
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowIcon(script_icon())
        self.document = document
        self._settings = settings if settings is not None else QSettings()
        self.user_dir = user_dir or T.user_script_dir()
        self.viewport = None                       # set by the main window; used to wait for a render pass
        self.runner = ScriptRunner(self)
        self._run: object = None
        self._run_started = 0.0
        self._run_updated = False
        self._snapshot: Flame | None = None
        self._last_run: ScriptResult | None = None
        self._last_run_info: dict = {}
        self.script_name = "untitled"
        self.script_path: Path | None = None
        self.template_id: str | None = None
        self.editor = CodeEditor(self)
        self.find_bar = FindBar(self.editor, self)
        self.output = OutputPanel(self)
        self.drawer = ScriptDrawer(self)
        self.splitter = CollapsibleSplitter(self, last_width=DRAWER_WIDTH, collapse_last=True)
        self.vsplitter = QSplitter(Qt.Orientation.Vertical, self)
        self.position_label = QLabel(self)
        self.state_label = QLabel(self)
        self.progress_bar = QProgressBar(self)
        self._build()
        self._build_actions()
        self._connect()
        self._load()
        self._wait_timer = QTimer(self, singleShot=True)
        self._wait_timer.timeout.connect(self._render_waited)
        self._waiting = False
        self.refresh_templates()
        self.refresh_info()
        self._refresh_context()

    # --- construction ---------------------------------------------------------------------------------------
    def _build(self) -> None:
        left = QWidget(self)
        column = QVBoxLayout(left)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        column.addWidget(self.find_bar)
        self.vsplitter.addWidget(self.editor)
        self.vsplitter.addWidget(self.output)
        self.vsplitter.setStretchFactor(0, 1)
        self.vsplitter.setStretchFactor(1, 0)
        self.vsplitter.setSizes([500, OUTPUT_HEIGHT])
        column.addWidget(self.vsplitter, 1)
        self.splitter.last_label = "documentation drawer"
        self.splitter.addWidget(left)
        self.splitter.addWidget(self.drawer)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.setCentralWidget(self.splitter)
        self.progress_bar.setFixedWidth(120)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.hide()
        self.statusBar().addWidget(self.position_label)
        self.statusBar().addPermanentWidget(self.progress_bar)
        self.statusBar().addPermanentWidget(self.state_label)
        self.resize(1180, 720)

    def _build_actions(self) -> None:
        def action(text: str, slot, shortcut: str = "", icon: str = "", tip: str = "", checkable: bool = False) -> QAction:
            a = QAction(text, self)
            if shortcut:
                a.setShortcut(QKeySequence(shortcut))
            if icon:
                a.setIcon(action_icon(icon))
            a.setToolTip(tip + (f" ({shortcut})" if shortcut else "") if tip else text)
            a.setStatusTip(tip or text)
            a.setCheckable(checkable)
            a.triggered.connect(slot)
            return a

        self.actionNew = action("New Script", self.new_script, "Ctrl+N", "new", "New script")
        self.actionOpen = action("Open Script…", self.open_script, "Ctrl+O", "open", "Open a script file")
        self.actionSave = action("Save Script", lambda: self.save_script(False), "Ctrl+S", "save", "Save the script")
        self.actionSaveAs = action("Save Script As…", lambda: self.save_script(True), "Ctrl+Shift+S", "save-as", "Save the script under a new name")
        self.actionRun = action("Run", self.run, "Ctrl+Return", "run", "Run the script on the fractal")
        self.actionStop = action("Stop", self.stop, "Shift+Esc", "stop", "Stop the running script")
        self.actionStop.setEnabled(False)
        self.actionUndo = action("Undo", self.editor.undo, "", "undo", "Undo the last edit in the script")
        self.actionRedo = action("Redo", self.editor.redo, "", "redo", "Redo")
        self.actionCut = action("Cut", self.editor.cut, "Ctrl+X")
        self.actionCopy = action("Copy", self.editor.copy, "Ctrl+C")
        self.actionPaste = action("Paste", self.editor.paste, "Ctrl+V")
        self.actionFind = action("Find…", lambda: self.find_bar.open(False), "", "find", "Find (Ctrl+F) / replace (Ctrl+H)")
        self.actionReplace = action("Replace…", lambda: self.find_bar.open(True))
        self.actionGoto = action("Go to Line…", self.goto_line)
        self.actionComment = action("Toggle Comment", self.editor.toggle_comment, "", "comment", "Comment / uncomment the selected lines (Ctrl+/)")
        self.actionIndent = action("Indent", self.editor.indent, "", "indent", "Indent the selected lines (Tab)")
        self.actionOutdent = action("Outdent", self.editor.outdent, "", "outdent", "Outdent the selected lines (Shift+Tab)")
        self.actionCheck = action("Check Syntax", self.check_syntax, "Ctrl+Shift+C", "check", "Check the script for syntax errors without running it")
        self.actionFlameToScript = action("Flame → Script", self.flame_to_script, "", "flame-script", "Generate a script that rebuilds the fractal shown in the main window")
        self.actionRevert = action("Revert Flame", self.revert_flame, "", "revert", "Put the fractal back as it was before the last run")
        self.actionRevert.setEnabled(False)
        self.actionSaveTemplate = action("Save as Template…", self.save_as_template, "", "template", "Keep the script as a template of your own")
        self.actionClearOutput = action("Clear Output", self.output.clear_output, "", "clear", "Clear the output panel")
        self.actionToggleDrawer = action("Show/Hide Drawer", self._toggle_drawer, "Ctrl+L", "drawer", "Show or hide the documentation drawer", checkable=True)
        self.actionToggleDrawer.setChecked(True)
        self.actionClose = action("Close Window", self.close, "Ctrl+W")
        self.actionGuide = action("Scripting Guide", lambda: self.show_reference("guide"), "F1")
        self.actionApi = action("API Reference", lambda: self.show_reference("api"))
        self.actionVariations = action("Variations", lambda: self.show_reference("variations"))
        self.actionTemplates = action("Templates", lambda: self.show_tab("templates"))
        self.actionInfo = action("Script Info", lambda: self.show_tab("info"))
        self.actionContext = action("Context Help", lambda: self.show_tab("context"))
        for a in (self.actionUndo, self.actionRedo):
            a.setEnabled(False)
        self.editor.undoAvailable.connect(self.actionUndo.setEnabled)
        self.editor.redoAvailable.connect(self.actionRedo.setEnabled)

        bar = self.menuBar()
        self.menuFile = bar.addMenu("File")
        for a in (self.actionNew, self.actionOpen, self.actionSave, self.actionSaveAs):
            self.menuFile.addAction(a)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionClose)
        self.menuEdit = bar.addMenu("Edit")
        for a in (self.actionUndo, self.actionRedo, None, self.actionCut, self.actionCopy, self.actionPaste, None, self.actionFind, self.actionReplace,
                  self.actionGoto, None, self.actionComment, self.actionIndent, self.actionOutdent):
            self.menuEdit.addAction(a) if a is not None else self.menuEdit.addSeparator()
        self.menuScript = bar.addMenu("Script")
        for a in (self.actionRun, self.actionStop, self.actionCheck, None, self.actionFlameToScript, self.actionRevert, None, self.actionSaveTemplate,
                  self.actionClearOutput):
            self.menuScript.addAction(a) if a is not None else self.menuScript.addSeparator()
        self.menuView = bar.addMenu("View")
        for a in (self.actionToggleDrawer, None, self.actionContext, self.actionGuide, self.actionApi, self.actionVariations, self.actionInfo, self.actionTemplates):
            self.menuView.addAction(a) if a is not None else self.menuView.addSeparator()

        self.toolBar = QToolBar("Script toolbar", self)
        self.toolBar.setMovable(False)
        self.toolBar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(self.toolBar)
        for a in (self.actionNew, self.actionOpen, self.actionSave, self.actionSaveAs, None, self.actionRun, self.actionStop, None, self.actionUndo,
                  self.actionRedo, None, self.actionFind, self.actionComment, self.actionOutdent, self.actionIndent, self.actionCheck, None,
                  self.actionFlameToScript, self.actionRevert, None, self.actionSaveTemplate, self.actionClearOutput, self.actionToggleDrawer):
            self.toolBar.addAction(a) if a is not None else self.toolBar.addSeparator()
        for a in (self.actionNew, self.actionOpen, self.actionSave, self.actionSaveAs, self.actionUndo, self.actionRedo, self.actionFind, self.actionComment,
                  self.actionOutdent, self.actionIndent, self.actionCheck, self.actionClearOutput, self.actionToggleDrawer):
            button = self.toolBar.widgetForAction(a)
            if button is not None:
                button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

    def _connect(self) -> None:
        self.editor.run_requested.connect(self.run)
        self.editor.find_requested.connect(self.find_bar.open)
        self.editor.goto_requested.connect(self.goto_line)
        self.editor.save_requested.connect(self.save_script)
        self.editor.context_changed.connect(self._refresh_context)
        self.editor.status.connect(lambda text: self.statusBar().showMessage(text, 3000))
        self.editor.textChanged.connect(self._on_text_changed)
        self.editor.cursorPositionChanged.connect(self._show_position)
        self.output.line_clicked.connect(self._jump_to_error)
        self.drawer.context.insert_requested.connect(self.insert_name)
        self.drawer.context.option_requested.connect(self.insert_option)
        self.drawer.reference.insert_requested.connect(self.insert_name)
        self.drawer.info.header_requested.connect(self.insert_header)
        self.drawer.info.copy_requested.connect(lambda: QGuiApplication.clipboard().setText(self.editor.text()))
        templates = self.drawer.templates
        templates.load_requested.connect(self.load_template)
        templates.insert_requested.connect(lambda t: self.editor.insert_snippet(T.strip_metadata(t.code)))
        templates.run_requested.connect(self.run_template)
        templates.save_requested.connect(self.save_as_template)
        templates.overwrite_requested.connect(self.overwrite_template)
        templates.rename_requested.connect(self.rename_template)
        templates.delete_requested.connect(self.delete_template)
        templates.refresh_requested.connect(self.refresh_templates)
        self.drawer.currentChanged.connect(lambda i: self._settings.setValue(TAB_KEY, i))
        self.splitter.last_collapsed_changed.connect(self._on_drawer_collapsed)
        self.runner.output.connect(self.output.append_text)
        self.runner.cleared.connect(self.output.clear_output)
        self.runner.message.connect(self._script_message)
        self.runner.progress.connect(self._script_progress)
        self.runner.input_requested.connect(self._script_input)
        self.runner.update_requested.connect(self._script_update)
        self.runner.finished.connect(self._script_finished)
        self.document.flame_replaced.connect(self._on_flame_changed)
        self.document.flame_restored.connect(self._on_flame_changed)

    # --- persistence ---------------------------------------------------------------------------------------------
    def _load(self) -> None:
        s = self._settings
        draft = s.value(DRAFT_KEY, None)
        self.editor.set_text(draft if isinstance(draft, str) and draft.strip() else DEFAULT_SCRIPT)
        path = s.value(FILE_KEY, "")
        self.script_path = Path(path) if path else None
        self.script_name = s.value(NAME_KEY, "") or (self.script_path.stem if self.script_path else "") or T.parse_metadata(self.editor.text()).get("name", "untitled")
        self.editor.document().setModified(s.value(MODIFIED_KEY, "false") in ("true", True, "True"))
        try:
            tab = int(s.value(TAB_KEY, 0))
            if 0 <= tab < self.drawer.count():
                self.drawer.setCurrentIndex(tab)
        except (TypeError, ValueError):
            pass
        geometry = s.value(GEOMETRY_KEY, None)
        if geometry is not None:
            self.restoreGeometry(geometry)
        if s.value(DRAWER_KEY, "false") in ("true", True, "True"):
            QTimer.singleShot(0, lambda: self.splitter.set_last_collapsed(True))
        self._update_title()

    def save_state(self) -> None:
        s = self._settings
        s.setValue(DRAFT_KEY, self.editor.text())
        s.setValue(FILE_KEY, str(self.script_path) if self.script_path else "")
        s.setValue(NAME_KEY, self.script_name)
        s.setValue(MODIFIED_KEY, self.editor.document().isModified())
        s.setValue(GEOMETRY_KEY, self.saveGeometry())
        s.setValue(DRAWER_KEY, self.splitter.is_last_collapsed())

    # --- window management --------------------------------------------------------------------------------------------
    def bring_to_front(self) -> None:
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
        self.show()
        self.raise_()
        self.activateWindow()
        self.editor.setFocus()

    def closeEvent(self, event) -> None:
        if self.runner.running and QMessageBox.question(self, WINDOW_TITLE, "A script is running. Stop it and close the editor?") != QMessageBox.StandardButton.Yes:
            event.ignore()
            return
        self.stop()
        self.save_state()
        super().closeEvent(event)

    def hideEvent(self, event) -> None:
        self.save_state()
        super().hideEvent(event)

    def _toggle_drawer(self, shown: bool) -> None:
        self.splitter.set_last_collapsed(not shown)

    def _on_drawer_collapsed(self, collapsed: bool) -> None:
        if self.actionToggleDrawer.isChecked() == collapsed:
            self.actionToggleDrawer.setChecked(not collapsed)
        self._settings.setValue(DRAWER_KEY, collapsed)

    def show_tab(self, name: str) -> None:
        """Open the drawer on one of its tabs (`context`, `reference`, `info`, `templates`)."""
        self.splitter.set_last_collapsed(False)
        self.drawer.show_tab(name)

    def show_reference(self, mode: str) -> None:
        self.show_tab("reference")
        self.drawer.reference.show_mode(mode)

    # --- title / status -------------------------------------------------------------------------------------------------
    def _update_title(self) -> None:
        self.setWindowTitle(f"{WINDOW_TITLE} — {self.script_name}[*]")
        self.setWindowModified(self.editor.document().isModified())
        self.actionSave.setEnabled(True)

    def _show_position(self) -> None:
        line, column = self.editor.line_column()
        self.position_label.setText(f"Ln {line}, Col {column}   ·   {self.editor.blockCount()} lines")

    def _on_text_changed(self) -> None:
        meta = T.parse_metadata(self.editor.text())
        if meta.get("name") and self.script_path is None and meta["name"] != self.script_name:
            self.script_name = meta["name"]
        self._update_title()
        self._show_position()
        self._info_timer_start()

    _info_timer: QTimer | None = None

    def _info_timer_start(self) -> None:
        if self._info_timer is None:
            self._info_timer = QTimer(self, singleShot=True, interval=400)
            self._info_timer.timeout.connect(self.refresh_info)
        self._info_timer.start()

    def _on_flame_changed(self) -> None:
        self._info_timer_start()

    # --- context / info -------------------------------------------------------------------------------------------------
    def _refresh_context(self) -> None:
        self.drawer.context.show_context(C.context(self.editor.text(), self.editor.position))

    def refresh_info(self) -> None:
        """Rebuild the Info tab."""
        code = self.editor.text()
        meta = T.parse_metadata(code)
        lines = code.split("\n")
        code_lines = [line for line in lines if line.strip() and not line.lstrip().startswith("#")]
        used = [n for n in D.GLOBALS if re.search(rf"(?<![\w.]){re.escape(n)}\b", code)]
        functions = re.findall(r"^\s*def\s+(\w+)", code, re.MULTILINE)
        prompts = bool(re.search(r"\b(input_text|input_number|confirm)\s*\(", code))
        updates = bool(re.search(r"\b(update|UpdateFlame)\s*\(", code))
        template = next((t for t in self._templates if t.id == self.template_id), None) if self.template_id else None
        tags = lambda names: " ".join(f"<code>{escape(n)}</code>" for n in names) or "—"   # noqa: E731
        script_rows = [
            ("Name", escape(meta.get("name") or self.script_name)),
            ("File", escape(str(self.script_path)) if self.script_path else "<i>not saved to a file</i>"),
            ("Status", "Modified (unsaved changes)" if self.editor.document().isModified() else "Saved"),
        ]
        for key in ("author", "version"):
            if meta.get(key):
                script_rows.append((key.capitalize(), escape(meta[key])))
        script_rows += [
            ("Description", escape(meta.get("description", "")) or "—"),
            ("Size", f"{len(lines)} lines, {len(code_lines)} code lines, {len(code)} characters"),
            ("Interaction", ("asks questions" if prompts else "no prompts") + (", updates the preview while running" if updates else "")),
            ("Functions", tags(functions)), ("API used", tags(used)),
        ]
        if template is not None:
            script_rows.append(("From template", escape(template.name) + (" (built-in)" if template.builtin else " (yours)")))
        run_rows: list[tuple[str, str]] = []
        info = self._last_run_info
        if self.runner.running:
            run_rows.append(("Result", "<span style='color: #e65100'>running…</span>"))
        elif info:
            outcome = info.get("outcome", "")
            color = "#2e7d32" if info.get("ok") else "#c62828"
            run_rows += [("Started", info.get("started", "")), ("Duration", f"{info.get('seconds', 0):.2f} s"),
                         ("Result", f"<span style='color: {color}'>{escape(outcome)}</span>"),
                         ("Transforms", f"{info.get('before', '?')} → {info.get('after', '?')}"), ("Output", f"{info.get('lines', 0)} lines")]
        else:
            run_rows.append(("Result", "not run yet"))
        flame = self.document.flame
        flame_rows = [("Flame", escape(flame.name) if flame else "<i>none loaded</i>")]
        if flame is not None:
            flame_rows += [("Transforms", f"{len(flame.xforms)}" + (" + final" if flame.final else "")),
                           ("Size", f"{flame.camera.width} × {flame.camera.height}"),
                           ("Source", escape(self.document.source_path.name) if self.document.source_path else "not from a file")]
        self.drawer.info.show_info([("Script", script_rows), ("Last run", run_rows), ("Fractal in the main window", flame_rows)])

    def insert_name(self, name: str, kind: str) -> None:
        """Insert a name from the documentation at the cursor, replacing a typed prefix it completes."""
        text = name + ("()" if kind in ("function", "method") else "")
        code, pos = self.editor.text(), self.editor.position
        cx = C.context(code, pos)
        prefix = cx.prefix if cx.kind in ("members", "prefix", "call") and cx.prefix and name.lower().startswith(cx.prefix.lower()) else ""
        self.editor.replace_range(pos - len(prefix), pos, text)
        if text.endswith("()"):
            entry = cx.entry if cx.kind == "symbol" else None
            has_params = True
            if kind == "function" and name in D.GLOBALS:
                has_params = bool(D.GLOBALS[name].params)
            elif entry is not None:
                has_params = bool(entry.params)
            if has_params:
                cursor = self.editor.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.Left)
                self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def insert_option(self, name: str) -> None:
        """Insert an option value (a variation name …) into the string being typed, or as a new quoted string."""
        code, pos = self.editor.text(), self.editor.position
        st = C.scan_state(code, pos)
        if st.in_string and len(st.in_string) == 1:
            quote = st.in_string
            closing = 1 if code[pos:pos + 1] == quote else 0
            self.editor.replace_range(st.string_start, pos + closing, name + quote)
        else:
            self.editor.insert_snippet(f"'{name}'")
        self.editor.setFocus()

    def insert_header(self) -> None:
        meta = T.parse_metadata(self.editor.text())
        code = T.with_metadata(self.editor.text(), name=meta.get("name") or self.script_name, author=meta.get("author") or " ",
                               description=meta.get("description") or " ")
        cursor = self.editor.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.insertText(code)
        self.editor.moveCursor(QTextCursor.MoveOperation.Start)
        self.editor.setFocus()

    def goto_line(self) -> None:
        line, ok = QInputDialog.getInt(self, "Go to line", "Line:", self.editor.line_column()[0], 1, max(1, self.editor.blockCount()))
        if ok:
            self.editor.goto_line(line)

    def _jump_to_error(self, line: int) -> None:
        self.editor.goto_line(line)
        self.editor.set_error_line(line)

    # --- running -----------------------------------------------------------------------------------------------------
    def run(self) -> None:
        """Run the editor's script on the main window's fractal."""
        if self.runner.running:
            return
        code = self.editor.text()
        self.editor.set_error_line(None)
        error = check_syntax(code)
        if error is not None:
            self.output.append_note(f"✖ {error}", "error", error.line)
            if error.line:
                self.editor.set_error_line(error.line)
                self.editor.goto_line(error.line, error.column or 1)
            self.statusBar().showMessage("Syntax error — see the output panel", 5000)
            return
        flame = self.document.flame
        self._snapshot = flame.copy() if flame is not None else None
        self._run = object()
        self._run_updated = False
        self._run_started = time.monotonic()
        self._last_run_info = {"started": time.strftime("%H:%M:%S"), "before": len(flame.xforms) if flame else 0}
        self.output.append_note(f"▶ Running {self.script_name}…", "info")
        self._set_running(True)
        self.refresh_info()
        self.runner.run(code, flame)

    def stop(self) -> None:
        if self.runner.running:
            self.runner.stop()
            self._wait_timer.stop()
            self._waiting = False
            self.statusBar().showMessage("Stopping…", 2000)

    def _set_running(self, running: bool) -> None:
        self.actionRun.setEnabled(not running)
        self.actionStop.setEnabled(running)
        self.state_label.setText("Running…" if running else "")
        self.progress_bar.setVisible(running)
        self.progress_bar.setValue(0)
        if running:
            self.progress_bar.setRange(0, 0)

    def _script_progress(self, fraction: float) -> None:
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(int(fraction * 100))

    def _script_message(self, text: str) -> None:
        self.output.append_note(f"[message] {text}", "info")
        QMessageBox.information(self, "Script message", text)

    def _script_input(self, kind: str, prompt: str, default: str) -> None:
        if kind == REQUEST_INPUT:
            value, ok = QInputDialog.getText(self, "Script input", prompt, text=default)
            self.runner.reply(value if ok else None)
        elif kind == REQUEST_CONFIRM:
            answer = QMessageBox.question(self, "Script question", prompt, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            self.runner.reply(answer == QMessageBox.StandardButton.Yes)
        else:
            self.runner.reply(None)

    def _script_update(self, flame: Flame, wait: bool) -> None:
        """`update()`: push the intermediate flame into the main window; reply when a pass has been rendered (or soon)."""
        self.document.apply_script(flame, self._run)
        self._run_updated = True
        self.actionRevert.setEnabled(True)
        if wait and self.viewport is not None:
            self._waiting = True
            self._wait_timer.start(RENDER_WAIT_MS)
            return
        self.runner.reply(None)

    def bind_viewport(self, viewport) -> None:
        """Let `update(wait=True)` wait for the viewport's first pass (the main window calls this)."""
        self.viewport = viewport
        viewport.render_progress.connect(self._on_render_pass)

    def _on_render_pass(self, _stats) -> None:
        if self._waiting:
            self._render_waited()

    def _render_waited(self) -> None:
        if self._waiting:
            self._waiting = False
            self._wait_timer.stop()
            self.runner.reply(None)

    def _script_finished(self, result: ScriptResult) -> None:
        self.output.flush()
        seconds = time.monotonic() - self._run_started
        info = self._last_run_info
        info.update(seconds=seconds, lines=result.output_lines, ok=result.ok)
        if result.ok:
            if result.flame is not None:
                self.document.apply_script(result.flame, self._run)
            self.actionRevert.setEnabled(self._snapshot is not None or result.flame is not None)
            count = len(result.flame.xforms) if result.flame is not None else 0
            what = "■ Stopped" + (f": {result.stop_reason}" if result.stop_reason and not result.user_stopped else " by you") if result.stopped else "✔ Finished"
            note = f"{what} after {seconds:.2f} s — {count} transform{'s' if count != 1 else ''}, fractal updated."
            self.output.append_note(note, "ok" if not result.user_stopped else "info")
            info.update(outcome="stopped" if result.stopped else "finished", after=count)
            self.statusBar().showMessage("Script finished" if not result.stopped else "Script stopped", 4000)
        else:
            error = result.error
            self.output.append_note(f"✖ {error} — fractal unchanged", "error", error.line)
            if error.details and error.details.count("\n") >= 1:
                self.output.append_note(error.details, "info")   # the call chain, when the error is inside a function
            if error.line:
                self.editor.set_error_line(error.line)
                self.editor.goto_line(error.line, error.column or 1)
            if self._run_updated and self._snapshot is not None:
                self.document.apply_script(self._snapshot, self._run)   # undo the intermediate updates
            info.update(outcome=str(error), after=info.get("before"))
            self.statusBar().showMessage("Script failed — see the output panel", 5000)
        self._set_running(False)
        self.refresh_info()

    def revert_flame(self) -> None:
        """Put the fractal back as it was before the last run (itself undoable)."""
        if self._snapshot is None:
            return
        self.document.apply_script(self._snapshot, None)
        self.output.append_note("↶ Fractal reverted to its state before the last run.", "info")

    def check_syntax(self) -> bool:
        error = check_syntax(self.editor.text())
        if error is None:
            self.editor.set_error_line(None)
            self.output.append_note("✔ Syntax OK", "ok")
            self.statusBar().showMessage("Syntax OK", 3000)
            return True
        self.output.append_note(f"✖ {error}", "error", error.line)
        if error.line:
            self.editor.set_error_line(error.line)
            self.editor.goto_line(error.line, error.column or 1)
        self.statusBar().showMessage("Syntax error", 3000)
        return False

    def flame_to_script(self) -> None:
        flame = self.document.flame
        if flame is None:
            QMessageBox.information(self, WINDOW_TITLE, "No fractal is loaded in the main window.")
            return
        if not self.confirm_discard():
            return
        self.load_code(flame_to_script(flame), f"Flame: {flame.name}")
        self.output.append_note(f"Generated a script from '{flame.name}'.", "info")

    # --- files ----------------------------------------------------------------------------------------------------------
    def confirm_discard(self) -> bool:
        """True if the current script may be replaced (asks when it has unsaved changes)."""
        if not self.editor.document().isModified():
            return True
        answer = QMessageBox.question(self, WINDOW_TITLE, f"The script '{self.script_name}' has unsaved changes. Discard them?",
                                      QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        return answer == QMessageBox.StandardButton.Discard

    def load_code(self, code: str, name: str | None = None, path: Path | None = None, template_id: str | None = None) -> None:
        """Put `code` in the editor (unmodified) and name the script."""
        self.editor.set_text(code)
        self.script_path = path
        self.script_name = name or T.parse_metadata(code).get("name") or (path.stem if path else "untitled")
        self.template_id = template_id
        self.editor.document().setModified(False)
        self._update_title()
        self.refresh_info()
        self.editor.setFocus()

    def new_script(self) -> None:
        if self.confirm_discard():
            self.load_code(DEFAULT_SCRIPT, "untitled")

    def _folder(self) -> str:
        return str(self._settings.value(FOLDER_KEY, "") or (self.user_dir if self.user_dir.is_dir() else Path.home()))

    def open_script(self) -> None:
        if not self.confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Open script", self._folder(), SCRIPT_FILTER)
        if path:
            self.open_path(Path(path))

    def open_path(self, path: Path) -> None:
        try:
            code = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            QMessageBox.warning(self, "Cannot open script", str(exc))
            return
        self.load_code(code, T.parse_metadata(code).get("name") or path.stem, path)
        self._settings.setValue(FOLDER_KEY, str(path.parent))
        self.output.append_note(f"Opened {path}", "info")

    def save_script(self, save_as: bool = False) -> bool:
        """Write the script to its file (asking for one the first time or on Save As); False if cancelled."""
        path = self.script_path
        if save_as or path is None:
            suggested = str(Path(self._folder()) / (T.safe_file_name(self.script_name) if path is None else path.name))
            chosen, _ = QFileDialog.getSaveFileName(self, "Save script", suggested, SCRIPT_FILTER)
            if not chosen:
                return False
            path = Path(chosen)
            if not path.suffix:
                path = path.with_suffix(".py")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self.editor.text(), encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, "Cannot save script", str(exc))
            return False
        self.script_path = path
        self.script_name = T.parse_metadata(self.editor.text()).get("name") or path.stem
        self.editor.document().setModified(False)
        self._settings.setValue(FOLDER_KEY, str(path.parent))
        self._update_title()
        self.refresh_info()
        self.statusBar().showMessage(f"Saved {path}", 4000)
        return True

    # --- templates ---------------------------------------------------------------------------------------------------------
    @property
    def templates_folder(self) -> Path:
        return self.user_dir / "templates"

    def refresh_templates(self) -> None:
        self._templates = T.all_templates(self.templates_folder)
        self.drawer.templates.set_templates(self._templates, self.templates_folder)

    def load_template(self, template: T.Template) -> bool:
        if not self.confirm_discard():
            return False
        self.load_code(template.code, template.name, None, template.id)
        self.statusBar().showMessage(f"Loaded template '{template.name}'", 3000)
        return True

    def run_template(self, template: T.Template) -> None:
        if self.load_template(template):
            self.run()

    def save_as_template(self) -> None:
        meta = T.parse_metadata(self.editor.text())
        name, ok = QInputDialog.getText(self, "Save as template", "Template name:", text=meta.get("name") or self.script_name)
        if not ok or not name.strip():
            return
        existing = next((t for t in self._templates if not t.builtin and t.name == name.strip()), None)
        if existing is not None and QMessageBox.question(self, "Save as template", f"A template named '{name}' exists. Overwrite it?") != QMessageBox.StandardButton.Yes:
            return
        template = T.save_user_template(name.strip(), self.editor.text(), meta.get("description", ""), self.templates_folder,
                                        existing.path if existing else None)
        self.template_id = template.id
        self.refresh_templates()
        self.drawer.templates.select(template.id)
        self.show_tab("templates")
        self.statusBar().showMessage(f"Template '{template.name}' saved to {template.path}", 5000)

    def overwrite_template(self, template: T.Template) -> None:
        if template.builtin or QMessageBox.question(self, "Overwrite template", f"Replace the template '{template.name}' with the script in the editor?") != QMessageBox.StandardButton.Yes:
            return
        meta = T.parse_metadata(self.editor.text())
        T.save_user_template(template.name, self.editor.text(), meta.get("description", template.description), self.templates_folder, template.path)
        self.refresh_templates()
        self.statusBar().showMessage(f"Template '{template.name}' updated", 3000)

    def rename_template(self, template: T.Template) -> None:
        if template.builtin:
            return
        name, ok = QInputDialog.getText(self, "Rename template", "New name:", text=template.name)
        if ok and name.strip():
            T.rename_user_template(template, name.strip())
            self.refresh_templates()

    def delete_template(self, template: T.Template) -> None:
        if template.builtin or QMessageBox.question(self, "Delete template", f"Delete the template '{template.name}'?") != QMessageBox.StandardButton.Yes:
            return
        T.delete_user_template(template)
        self.refresh_templates()


__all__ = ["ScriptEditorWindow", "FindBar", "OutputPanel", "DEFAULT_SCRIPT", "WINDOW_TITLE"]
