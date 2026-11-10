"""The Script Editor window: write and run Python scripts that edit the fractal shown in the main window.

Opened from *Windows ▸ Script Editor* (`F8`) or the toolbar. Like the Gradient Library it is a tool window
of the main window: closing it hides it and the script is kept (and remembered between runs in QSettings).

Layout: a toolbar (New / Open / Save / Save As · Run / Stop · Record · Undo / Redo · Find, Comment, Indent, Outdent ·
Check syntax · Flame → Script · Revert flame · Save as template · Clear output · Drawer), the code editor
with an output panel beneath it on the left, and on the right a sliding drawer (collapsible like the main
window's panels) with five tabs — *Context* (dynamic documentation), *Reference* (guide + API), *Info*
(about this script), *Templates* and *Parameters*.

A script runs on a worker thread against a copy of the flame (`ScriptRunner`); `print` output streams into the
output panel, prompts pop up dialogs, `update()` pushes intermediate results into the main window, and the
result replaces the fractal as one undo step. Errors are reported with their line (click to jump there).
Runs are seeded, so a script's random numbers can be repeated.

The window coordinates helpers: `LiveParameters` (`script_live.py`: the Parameters tab's controls and the live
re-runs they drive — a re-run is a `rerunning` state of the run machine, superseded by Run) and `ScriptRecorder`
(`script_recorder.py`: Record). `run_code()` runs any code without putting it in the editor (the main window's
pinned templates).
"""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication, QTextCursor
from PySide6.QtWidgets import (
    QFileDialog, QInputDialog, QLabel, QMainWindow, QMessageBox, QProgressBar, QSplitter, QVBoxLayout, QWidget,
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
from ..widgets.icons import script_icon
from .fractal_document import FractalDocument
from .script_console import ConsolePanel, console_code
from .script_drawer import ScriptDrawer
from .script_editor_actions import build_actions
from .script_output import OutputPanel
from .script_live import ORIGIN_EDITOR, LiveParameters
from .script_recorder import ScriptRecorder
from .script_info import info_facts
from .script_templates import TemplateActions
from .script_runner import REQUEST_CONFIRM, REQUEST_INPUT, ScriptRunner
from .undo_labels import undo_label
from ..machines import SCRIPT_RUN, ScriptState
from ..widgets.windows import bring_to_front

WINDOW_TITLE = "Script Editor"
RUN_STATE_LABELS = {ScriptState.IDLE: "", ScriptState.RUNNING: "Running…",
                    ScriptState.WAITING: "Running — waiting for the viewport…", ScriptState.STOPPING: "Stopping…",
                    ScriptState.RERUNNING: "Updating the live parameters…", ScriptState.SUPERSEDED: "Stopping the live update…"}
DRAWER_WIDTH = 400
OUTPUT_HEIGHT = 150
RENDER_WAIT_MS = 2500
DRAFT_KEY = "script/draft"
RECORD_STYLE_KEY = "script/record_style"
RECORDED_HEADER = "# @name Recorded script\n# @description Edits recorded in Fractalchemy (Script ▸ Record)\n\n"
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


class ScriptEditorWindow(QMainWindow):
    """The Script Editor tool window, bound to the main window's document.

    Signals:
        explore_requested(): The Parameters tab's *Explore…* (the main window opens Mutate & Breed's Explore tab).
        batch_requested(): *Script ▸ Run on Many Fractals…*.
        recording_changed(bool): Record was switched on or off.
    """
    explore_requested = Signal()
    batch_requested = Signal()
    recording_changed = Signal(bool)

    def __init__(self, document: FractalDocument, parent: QWidget | None = None, settings: QSettings | None = None,
                 user_dir: Path | None = None, gradient_hint=None):
        """Args:
            document: The fractal scripts act on.
            parent: Owning window; when given this becomes a child top-level window.
            settings: Where the draft, layout and preferences persist (the application's store by default).
            user_dir: Folder for the user's scripts and templates (default `templates.user_script_dir()`).
            gradient_hint: Returns the Gradient Library's current gradient (the recorder writes its nodes).
        """
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowIcon(script_icon())
        self.document = document
        self._settings = settings if settings is not None else QSettings()
        self.user_dir = user_dir or T.user_script_dir()
        self.viewport = None                       # set by the main window; used to wait for a render pass
        self.animation_provider = None             # set by the main window: returns the Animation window (*Animate…*)
        self._gradient_hint = gradient_hint
        self.runner = ScriptRunner(self)
        self._run: object = None
        self._run_started = 0.0
        self._run_updated = False
        self._snapshot: Flame | None = None
        self._last_run: ScriptResult | None = None
        self.last_run_info: dict = {}
        self.script_name = "untitled"
        self.script_path: Path | None = None
        self.template_id: str | None = None
        self.editor = CodeEditor(self)
        self.find_bar = FindBar(self.editor, self)
        self.output = OutputPanel(self)
        self.console = ConsolePanel(self._settings, self)
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
        self._run_kind = "run"                           # what the runner's thread is doing: a full "run" or a live "rerun"
        self._run_name = self.script_name
        self._pending_run: tuple | None = None          # the Run that superseded a live re-run (machines.SCRIPT_RUN)
        self.recorder = ScriptRecorder(document, self.editor, gradient_hint, self)
        self.recorder.recording_changed.connect(self._on_recording_changed)
        self.set_record_style(self._record_style())
        self._parameters_shown: set[str] = set()       # scripts whose Parameters tab was brought forward once
        self.run_state = SCRIPT_RUN.new(WINDOW_TITLE)     # idle → running ⇄ waiting → stopping → idle, and live re-runs
        self.live = LiveParameters(self)
        self.templates = TemplateActions(self)
        self.pins = self.templates.pins
        self.drawer.parameters.explore_requested.connect(self.explore_requested.emit)
        self.drawer.parameters.animate_requested.connect(self.animate_parameter)
        self.run_state.on_change(lambda _step: self.show_run_state())
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
        lower = QWidget(self)
        lower_column = QVBoxLayout(lower)
        lower_column.setContentsMargins(0, 0, 0, 0)
        lower_column.setSpacing(0)
        lower_column.addWidget(self.output, 1)
        lower_column.addWidget(self.console)
        self.vsplitter.addWidget(lower)
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
        build_actions(self)

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
        self.drawer.currentChanged.connect(lambda i: self._settings.setValue(TAB_KEY, i))
        self.splitter.last_collapsed_changed.connect(self._on_drawer_collapsed)
        self.runner.output.connect(self._on_output)
        self.console.line.submitted.connect(self.run_console)
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
        bring_to_front(self)
        self.editor.setFocus()

    def closeEvent(self, event) -> None:
        if self.run_state.state in (ScriptState.RUNNING, ScriptState.WAITING) and QMessageBox.question(self, WINDOW_TITLE, "A script is running. Stop it and close the editor?") != QMessageBox.StandardButton.Yes:
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

    @property
    def settings(self) -> QSettings:
        """Where the window's draft, layout and preferences persist."""
        return self._settings

    @staticmethod
    def example_param_line() -> str:
        """What the Parameters tab's *Insert example* inserts."""
        return "angle = param('Angle', 30, min=-180, max=180)\n"

    def auto_show_parameters(self) -> bool:
        """Whether a run that declared parameters should bring the Parameters tab forward: the first time for a script."""
        key = str(self.script_path or self.script_name)
        if key in self._parameters_shown:
            return False
        self._parameters_shown.add(key)
        return True


    def _on_text_changed(self) -> None:
        meta = T.parse_metadata(self.editor.text())
        if meta.get("name") and self.script_path is None and meta["name"] != self.script_name:
            self.script_name = meta["name"]
        self._update_title()
        self._show_position()
        self._info_timer_start()
        if hasattr(self, "live"):
            self.live.refresh_code_changed()

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
        self.drawer.info.show_info(info_facts(self))

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
        """Run the editor's script on the main window's fractal (only when no run is in progress — the previous run's
        result included, which arrives a moment after its thread has ended; a live re-run in flight is superseded)."""
        self.run_code(self.editor.text(), self.script_name, origin=ORIGIN_EDITOR)

    def run_code(self, code: str, name: str, parameters: dict | None = None, origin: str = ORIGIN_EDITOR) -> bool:
        """Run `code` on the fractal as one undoable step, named `name`, without putting it in the editor when `origin` is
        not the editor (the main window's pinned templates). `parameters` default to the Parameters tab's changed
        values. Returns False when it could not start (another run, a syntax error)."""
        if self.run_state.state == ScriptState.RERUNNING:
            self._pending_run = (code, name, parameters, origin)
            self.live.superseded()
            self.runner.stop()
            self.run_state.fire("run")                      # → superseded: the Run starts when the re-run's result is in
            return True
        if not self.run_state.can("run"):
            return False
        self.editor.set_error_line(None)
        error = check_syntax(code)
        if error is not None:
            self.output.append_note(f"✖ {error}", "error", error.line)
            if error.line and origin == ORIGIN_EDITOR:
                self.editor.set_error_line(error.line)
                self.editor.goto_line(error.line, error.column or 1)
            self.statusBar().showMessage("Syntax error — see the output panel", 5000)
            return False
        if self.recorder is not None:
            self.recorder.stop()                            # recording ends when a script runs (its result is not recorded)
        flame = self.document.flame
        self._snapshot = flame.copy() if flame is not None else None
        self._run = object()
        self._run_kind = "run"
        self._run_updated = False
        self._run_name = name
        self._run_started = time.monotonic()
        self.last_run_info = {"started": time.strftime("%H:%M:%S"), "before": len(flame.xforms) if flame else 0}
        seed = self.live.seed_for_run()
        values = dict(parameters) if parameters is not None else self.live.values_for_run()
        self.live.on_run_started(code, self._snapshot, self._run, seed, name, origin)
        self.output.end_live_section()
        where = {ORIGIN_EDITOR: "", "palette": " (from the command palette)"}.get(origin, " (from the Scripts menu)")
        self.output.append_note(f"▶ Running {name}{where}…", "info")
        self.run_state.fire("run")
        self.refresh_info()
        self.runner.run(code, flame, seed=seed, parameters=values)
        return True

    # --- recording ---------------------------------------------------------------------------------------------------------
    def set_recording(self, on: bool) -> bool:
        """Record on / off. Starting on the untouched default script begins a new *Recorded script*."""
        if not on:
            self.recorder.stop()
            return False
        if self.document.flame is None:
            self.actionRecord.setChecked(False)
            self.statusBar().showMessage("Open a fractal first: recording writes the code for its edits", 5000)
            return False
        if self.editor.text() == DEFAULT_SCRIPT and not self.editor.document().isModified():
            self.load_code(RECORDED_HEADER, "Recorded script")
            self.editor.moveCursor(QTextCursor.MoveOperation.End)
        started = self.recorder.start(self._record_style())
        self.actionRecord.setChecked(started)
        return started

    def set_record_style(self, style: str) -> None:
        """*Record Values* (`absolute`) or *Record Changes* (`relative`)."""
        self.actionRecordValues.setChecked(style == "absolute")
        self.actionRecordChanges.setChecked(style == "relative")
        self.recorder.style = style
        self._settings.setValue(RECORD_STYLE_KEY, style)

    def _record_style(self) -> str:
        style = self._settings.value(RECORD_STYLE_KEY, "absolute")
        return style if style in ("absolute", "relative") else "absolute"

    def _on_recording_changed(self, recording: bool) -> None:
        if self.actionRecord.isChecked() != recording:
            self.actionRecord.setChecked(recording)
        self.show_run_state()
        self.recording_changed.emit(recording)

    def run_console(self, line: str) -> bool:
        """Run one console line against the fractal: an expression echoes its value, plain variables carry over to the
        next line, and a line that changes the fractal is one undo step named after it. Recorded as typed while Record
        is on."""
        if not self.run_state.can("run"):
            self.output.append_note("The console waits while a script runs.", "info")
            return False
        console = self.console.line
        code, self._console_offset = console_code(line, console.variables)
        console.remember(line)
        console.set_text("")
        self.output.end_live_section()
        self.output.append_note(">>> " + line.replace("\n", "\n... "), "info")
        if self.recorder is not None and self.recorder.recording:
            self.recorder.insert_code(line)
        flame = self.document.flame
        self._run = object()
        self._run_kind = "console"
        self._run_name = line if len(line) <= 40 else line[:39] + "…"
        self._run_updated = False
        self._snapshot = flame.copy() if flame is not None else None
        self._run_started = time.monotonic()
        self.run_state.fire("run")
        self.runner.run(code, flame, seed=self.live.seed_for_run())
        return True

    def _console_finished(self, result: ScriptResult) -> None:
        self._run_kind = "run"
        self.output.flush()
        console = self.console.line
        if result.ok:
            console.variables.update(result.variables)
            if result.flame is not None:
                self.document.apply_script(result.flame, self._run, label=undo_label("console", self._run_name))
        else:
            error = result.error
            line = error.line - self._console_offset if error.line else None
            self.output.append_note(f"✖ {error.kind}: {error.message}" + (f" (line {line})" if line and line > 1 else ""), "error")
        self.run_state.fire("finished")

    def start_rerun(self, code: str, flame: Flame | None, seed: int, values: dict, restricted: str) -> None:
        """A live-parameter re-run (`LiveParameters`): restricted, on the pre-run snapshot, the same undo step."""
        self._run_kind = "rerun"
        self.run_state.fire("rerun")
        self.runner.run(code, flame, seed=seed, parameters=values, restricted=restricted)

    def run_label(self, name: str | None = None) -> str:
        """The undo step's name for a run ("Script: Random rotate")."""
        return undo_label("script", name if name is not None else self._run_name)

    def _run_label(self) -> str:
        return self.run_label()

    @property
    def running(self) -> bool:
        """True from Run until the run's result has been processed (stopping, waiting for the viewport and live re-runs
        included)."""
        return self.run_state.state != ScriptState.IDLE

    def stop(self) -> None:
        """Ask the running script to stop (it ends at its next line, or at once when it waits)."""
        if self.run_state.can("stop"):
            if self.run_state.state == ScriptState.SUPERSEDED:
                self._pending_run = None
            self.live.stop_requested()
            self.runner.stop()
            self._wait_timer.stop()
            self.run_state.fire("stop")

    def show_run_state(self) -> None:
        """Actions, the state label and the progress bar from the run's state. A quick live re-run changes nothing
        visible (no flicker while a slider moves); a slow one shows Stop and the busy bar."""
        state = self.run_state.state
        quiet_rerun = state == ScriptState.RERUNNING and not self.live.busy
        running = state != ScriptState.IDLE and not quiet_rerun
        self.actionRun.setEnabled(self.run_state.can("run"))
        self.actionStop.setEnabled(self.run_state.can("stop") and not quiet_rerun)
        label = RUN_STATE_LABELS[state] if not quiet_rerun else ""
        if not label and self.recorder.recording:
            label = "● Recording"
        self.state_label.setText(label)
        if running != self.progress_bar.isVisible():
            self.progress_bar.setVisible(running)
            self.progress_bar.setValue(0)
            if running:
                self.progress_bar.setRange(0, 0)

    _show_run_state = show_run_state

    def _on_output(self, text: str) -> None:
        """`print` text: into the output panel, or — for a live re-run — into the live section when it ends."""
        if self._run_kind == "rerun":
            self.live.collect_output(text)
        else:
            self.output.append_text(text)

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
        self.document.apply_script(flame, self._run, label=self._run_label())
        self._run_updated = True
        self.actionRevert.setEnabled(True)
        if wait and self.viewport is not None and self.run_state.fire_if("wait"):    # not while stopping: reply at once
            self._wait_timer.start(RENDER_WAIT_MS)
            return
        self.runner.reply(None)

    def bind_viewport(self, viewport) -> None:
        """Let `update(wait=True)` wait for the viewport's first pass (the main window calls this)."""
        self.viewport = viewport
        viewport.render_progress.connect(self._on_render_pass)

    def _on_render_pass(self, _stats) -> None:
        if self.run_state.state == ScriptState.WAITING:
            self._render_waited()

    def _render_waited(self) -> None:
        """The viewport rendered the intermediate fractal (or the wait timed out): let the script go on."""
        if self.run_state.fire_if("rendered"):
            self._wait_timer.stop()
            self.runner.reply(None)

    def _script_finished(self, result: ScriptResult) -> None:
        if self._run_kind == "rerun":
            self._rerun_finished(result)
        elif self._run_kind == "console":
            self._console_finished(result)
        else:
            self._full_run_finished(result)

    def _rerun_finished(self, result: ScriptResult) -> None:
        superseded = self.run_state.state == ScriptState.SUPERSEDED
        self._run_kind = "run"
        self.run_state.fire("finished")
        self.live.on_rerun_finished(result)
        pending, self._pending_run = self._pending_run, None
        if superseded and pending is not None:
            self.run_code(*pending)

    def _full_run_finished(self, result: ScriptResult) -> None:
        self.output.flush()
        seconds = time.monotonic() - self._run_started
        info = self.last_run_info
        info.update(seconds=seconds, lines=result.output_lines, ok=result.ok)
        if result.ok:
            if result.flame is not None:
                self.document.apply_script(result.flame, self._run, label=self._run_label())
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
        self.run_state.fire("finished")
        self.live.on_run_finished(result)
        info.update(parameters=len(result.declarations), live=self.live.live)
        self.refresh_info()

    def revert_flame(self) -> None:
        """Put the fractal back as it was before the last run (itself undoable)."""
        if self._snapshot is None:
            return
        self.document.apply_script(self._snapshot, None, label="Revert flame")
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
        """Put `code` in the editor (unmodified) and name the script (another script: recording and the live session end)."""
        if self.recorder is not None:
            self.recorder.stop()
        self.live.unload()
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

    # --- templates (script_templates.TemplateActions) ---------------------------------------------------------------------
    @property
    def templates_folder(self) -> Path:
        return self.user_dir / "templates"

    @property
    def _templates(self) -> list[T.Template]:
        return self.templates.templates

    def all_templates(self) -> list[T.Template]:
        """Every template (yours, then the built-in ones), as the Templates tab lists them."""
        return list(self.templates.templates)

    def refresh_templates(self) -> None:
        self.templates.refresh()

    def load_template(self, template: T.Template) -> bool:
        return self.templates.load(template)

    def save_as_template(self) -> None:
        self.templates.save_as()

    def overwrite_template(self, template: T.Template) -> None:
        self.templates.overwrite(template)

    def delete_template(self, template: T.Template) -> None:
        self.templates.delete(template)

    def animate_parameter(self, name: str) -> None:
        """The Parameters tab's *Animate…*: keyframes of the script's result while one parameter sweeps."""
        from .script_animate import AnimateParameterDialog
        if self.animation_provider is None or self.live.session is None:
            self.statusBar().showMessage("Animating a parameter needs the Animation window (run the script first)", 5000)
            return
        AnimateParameterDialog(self.live, name, self.animation_provider(), self).exec()


__all__ = ["ScriptEditorWindow", "FindBar", "OutputPanel", "DEFAULT_SCRIPT", "WINDOW_TITLE"]
