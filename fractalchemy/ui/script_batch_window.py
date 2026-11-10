"""*Run a Script on Many Fractals*: one script applied to a whole set of flames, the results written to a file.

A `JobWindowBase` (Start / Pause / Stop, the elapsed clock, "quit while it runs?"): the options on the left —

* **Script**: the one in the Script Editor, or any template; its parameters from the Parameters tab (the values you set
  there) or the declared defaults;
* **Fractals**: the Fractal Library's selection (files and entries), every flame of a file, the *Randomly Generated*
  batch, or just the current fractal;
* **Output**: a `.fa` / `.flame` / `.chaos` file (created, or appended to — never overwritten), how results are named,
  whether every flame gets the same random numbers, and whether to stop at the first failure —

and the progress on the right: the count, the flame being worked on and a list of every outcome (✔, ✖ with the error,
⚠ for results that blow up). The job (`ScriptBatchJob`) reads the sources, runs `scripting.batch.apply_to_flames` —
restricted, so prompts, `update()` and `save_flame` are refused — and appends each result as it comes, so a stopped
batch keeps what it made. The source files are never written.
"""

from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QSettings, QThread, Signal
from PySide6.QtWidgets import (QButtonGroup, QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QPushButton, QRadioButton, QVBoxLayout, QWidget)

from ..fractal.formats import fractal_format_for, load_flames, open_dialog_filter, save_dialog_filter
from ..fractal.mutation import is_stable
from ..fractal.scene import Flame
from ..library.items import Kind, LibraryItem
from ..render.control import RenderControl
from ..scripting import templates as T
from ..scripting.batch import NAME_PATTERNS, SEED_PER_FLAME, SEED_SAME, BatchItem, BatchSpec, apply_to_flames
from ..widgets.icons import script_icon
from ..widgets.theming import colored_html
from .job_window import JobWindowBase

WINDOW_TITLE = "Run a Script on Many Fractals"
SOURCE_SELECTION, SOURCE_FILE, SOURCE_BATCH, SOURCE_CURRENT = "selection", "file", "batch", "current"
EDITOR_SCRIPT = "(the script in the Script Editor)"
SETTINGS_PREFIX = "script_batch/"


@dataclass
class BatchProgress:
    """What the job reports after every flame."""
    done: int = 0
    total: int = 0
    current: str = ""
    item: BatchItem | None = None
    phase: str = "Running"


@dataclass
class BatchOutcome:
    output: Path
    succeeded: int = 0
    failed: int = 0
    stopped: bool = False
    seconds: float = 0.0
    errors: list[str] = field(default_factory=list)


class ScriptBatchJob(QThread):
    """Reads the sources, runs the script on each flame and appends every result to the output file."""
    progressed = Signal(object)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, spec: BatchSpec, sources: list, output: Path, parent=None):
        """Args:
            spec: The script and how to run it.
            sources: `Flame`s, or `(path, index)` / `(path, None)` (every flame of the file) to read on the thread.
            output: The file the results are appended to.
        """
        super().__init__(parent)
        self.spec, self.sources, self.output = spec, sources, Path(output)
        self.control = RenderControl()
        self._stop = threading.Event()

    def pause(self) -> None:
        self.control.pause()

    def resume(self) -> None:
        self.control.resume()

    def cancel(self) -> None:
        self.control.cancel()
        self._stop.set()

    @property
    def paused(self) -> bool:
        return self.control.paused

    def _flames(self):
        for source in self.sources:
            if isinstance(source, Flame):
                yield source
                continue
            path, index = source
            try:
                flames = load_flames(path)
            except Exception as exc:  # noqa: BLE001 - an unreadable source is reported and skipped
                self.progressed.emit(BatchProgress(phase="Skipped", current=f"{Path(path).name}: {exc}"))
                continue
            yield from (flames if index is None else flames[index:index + 1])

    def run(self) -> None:  # noqa: D401 - QThread entry point
        started = time.monotonic()
        try:
            flames = list(self._flames())
            fmt = fractal_format_for(self.output)
            outcome = BatchOutcome(self.output)

            def each(item: BatchItem) -> None:
                if item.ok:
                    fmt.append(item.flame, self.output)
                    outcome.succeeded += 1
                else:
                    outcome.failed += 1
                    outcome.errors.append(f"{item.source_name}: {item.error}")
                self.progressed.emit(BatchProgress(item.index + 1, len(flames), item.source_name, item))
                if not self.control.wait_if_paused():
                    self._stop.set()

            self.progressed.emit(BatchProgress(0, len(flames), flames[0].name if flames else ""))
            report = apply_to_flames(self.spec, flames, self._stop, each, check=lambda f: is_stable(f, []))
            outcome.stopped = report.stopped
            outcome.seconds = time.monotonic() - started
            self.succeeded.emit(outcome)
        except Exception as exc:  # noqa: BLE001 - any failure ends in a message, not a dead thread
            self.failed.emit(str(exc))


class BatchProgressPanel(QWidget):
    """The right-hand side: count, current flame, every outcome."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.phase = QLabel("Ready", self)
        self.note = QLabel(self)
        self.elapsed = QLabel(self)
        self.results = QListWidget(self)
        self.outcome = QLabel(self)
        self.outcome.setWordWrap(True)
        self.outcome.setOpenExternalLinks(False)
        self.show_button = QPushButton("Show the result file", self)
        self.show_button.hide()
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        row.addWidget(self.phase, 1)
        row.addWidget(self.note)
        row.addWidget(self.elapsed)
        layout.addLayout(row)
        layout.addWidget(self.results, 1)
        layout.addWidget(self.outcome)
        layout.addWidget(self.show_button)

    def clear_result(self) -> None:
        self.results.clear()
        self.outcome.setText("")
        self.show_button.hide()

    def show_progress(self, progress: BatchProgress) -> None:
        if progress.phase == "Skipped":
            self.results.addItem(f"⚠ skipped {progress.current}")
            return
        self.phase.setText(f"{progress.done} of {progress.total}" + (f" — {progress.current}" if progress.current else ""))
        item = progress.item
        if item is not None:
            mark = "✔" if item.ok and not item.unstable else "⚠" if item.ok else "✖"
            text = f"{mark} {item.source_name}" + (f" → {item.flame.name}" if item.ok and item.flame.name != item.source_name else "")
            if item.error:
                text += f": {item.error}"
            elif item.unstable:
                text += " (blows up or collapses)"
            self.results.addItem(text)
            self.results.scrollToBottom()

    def show_note(self, note: str) -> None:
        self.note.setText(f"({note})" if note else "")

    def show_elapsed(self, seconds: float) -> None:
        self.elapsed.setText(f"{seconds:.0f} s")

    def show_failure(self, message: str) -> None:
        self.outcome.setText(colored_html(f"Failed: {message}", "error"))

    def show_outcome(self, outcome: BatchOutcome) -> None:
        what = "Stopped" if outcome.stopped else "Finished"
        text = f"{what}: {outcome.succeeded} fractal{'s' if outcome.succeeded != 1 else ''} written to {outcome.output.name}"
        if outcome.failed:
            text += f", {outcome.failed} failed"
        self.outcome.setText(colored_html(text, "warning" if outcome.failed or outcome.stopped else "success"))
        self.show_button.setVisible(outcome.succeeded > 0)


class ScriptBatchWindow(JobWindowBase):
    """The window (see the module docstring)."""
    title = WINDOW_TITLE
    quit_question = "A script is still running on many fractals. Stop it and quit?"

    def __init__(self, editor: Callable[[], object], selection: Callable[[], list[LibraryItem]], generated: Callable[[], list[Flame]],
                 current: Callable[[], Flame | None], parent: QWidget | None = None, settings: QSettings | None = None,
                 note_write: Callable[[Path], None] | None = None, show_file: Callable[[Path], None] | None = None):
        """Args:
            editor: Returns the Script Editor (its script, its templates, its Parameters tab values).
            selection: The Fractal Library's selected rows.
            generated: The *Randomly Generated* batch.
            current: The main window's fractal.
            note_write: Called before the output file is written (the library watcher then ignores our writes).
            show_file: Shows the output file in the library's temporary area.
        """
        super().__init__(parent, settings)
        self.setWindowIcon(script_icon())
        self._editor, self._selection, self._generated, self._current = editor, selection, generated, current
        self._note_write = note_write or (lambda _p: None)
        self._show_file = show_file or (lambda _p: None)
        self.last_outcome: BatchOutcome | None = None
        self.script_box = QComboBox(self)
        self.values_box = QComboBox(self)
        self.values_box.addItems(["The values set in the Parameters tab", "The declared defaults"])
        self.source_buttons = {key: QRadioButton(text, self) for key, text in (
            (SOURCE_SELECTION, "The fractals selected in the Fractal Library"), (SOURCE_FILE, "Every fractal of a file:"),
            (SOURCE_BATCH, "The Randomly Generated batch"), (SOURCE_CURRENT, "Only the current fractal"))}
        self.source_group = QButtonGroup(self)
        for button in self.source_buttons.values():
            self.source_group.addButton(button)
        self.source_file = QLineEdit(self)
        self.source_browse = QPushButton("…", self)
        self.output_path = QLineEdit(self)
        self.output_browse = QPushButton("…", self)
        self.names_box = QComboBox(self)
        self.names_box.addItems(NAME_PATTERNS)
        self.names_box.setEditable(True)
        self.seeds_box = QComboBox(self)
        self.seeds_box.addItem("New random numbers for every fractal", SEED_PER_FLAME)
        self.seeds_box.addItem("The same random numbers for every fractal", SEED_SAME)
        self.errors_box = QComboBox(self)
        self.errors_box.addItems(["Skip fractals that fail and go on", "Stop at the first failure"])
        self.summary = QLabel(self)
        self.summary.setWordWrap(True)
        self.progress_panel = BatchProgressPanel(self)
        self._panels = self._make_panels()
        self._build_layout(self.progress_panel, (980, 620), options_width=440)
        self.start_button.setText("Start")
        self._load()
        self._connect()

    # --- construction --------------------------------------------------------------------------------------------------
    def _make_panels(self) -> list[QWidget]:
        script = QGroupBox("Script", self)
        form = QFormLayout(script)
        form.addRow("Run", self.script_box)
        form.addRow("Parameters", self.values_box)
        sources = QGroupBox("Fractals", self)
        column = QVBoxLayout(sources)
        for key, button in self.source_buttons.items():
            column.addWidget(button)
            if key == SOURCE_FILE:
                row = QHBoxLayout()
                row.addWidget(self.source_file, 1)
                row.addWidget(self.source_browse)
                column.addLayout(row)
        output = QGroupBox("Results", self)
        form2 = QFormLayout(output)
        row = QHBoxLayout()
        row.addWidget(self.output_path, 1)
        row.addWidget(self.output_browse)
        form2.addRow("Add to file", row)
        form2.addRow("Names", self.names_box)
        form2.addRow("Random numbers", self.seeds_box)
        form2.addRow("On failure", self.errors_box)
        return [script, sources, output]

    def _option_widgets(self) -> list[QWidget]:
        return [*self._panels, self.summary]

    def _option_panels(self) -> list[QWidget]:
        return list(self._panels)

    def _connect(self) -> None:
        for widget in (self.script_box, self.values_box, self.names_box, self.seeds_box, self.errors_box):
            widget.currentIndexChanged.connect(self._on_options_changed)
        self.names_box.editTextChanged.connect(self._on_options_changed)
        self.source_group.buttonToggled.connect(lambda *_a: self._on_options_changed())
        self.source_file.textChanged.connect(self._on_options_changed)
        self.output_path.textChanged.connect(self._on_options_changed)
        self.source_browse.clicked.connect(self._browse_source)
        self.output_browse.clicked.connect(self._browse_output)
        self.progress_panel.show_button.clicked.connect(lambda: self._show_file(Path(self.output_path.text())))

    def _load(self) -> None:
        s = self._settings
        self.output_path.setText(str(s.value(SETTINGS_PREFIX + "output", "") or ""))
        self.source_file.setText(str(s.value(SETTINGS_PREFIX + "source_file", "") or ""))
        self.names_box.setCurrentText(str(s.value(SETTINGS_PREFIX + "names", NAME_PATTERNS[0]) or NAME_PATTERNS[0]))
        self.refresh_sources()

    def _persist(self) -> None:
        s = self._settings
        s.setValue(SETTINGS_PREFIX + "output", self.output_path.text())
        s.setValue(SETTINGS_PREFIX + "source_file", self.source_file.text())
        s.setValue(SETTINGS_PREFIX + "names", self.names_box.currentText())

    # --- what is offered -------------------------------------------------------------------------------------------------
    def refresh_sources(self, prefer: str | None = None) -> None:
        """Offer the scripts and the sources that exist now (called when the window is shown)."""
        current = self.script_box.currentText()
        self.script_box.blockSignals(True)
        self.script_box.clear()
        self.script_box.addItem(EDITOR_SCRIPT)
        for template in self._editor().all_templates():
            self.script_box.addItem(template.name, template)
        index = self.script_box.findText(current)
        self.script_box.setCurrentIndex(max(0, index))
        self.script_box.blockSignals(False)
        available = {SOURCE_SELECTION: bool(self._library_sources()), SOURCE_FILE: True, SOURCE_BATCH: bool(self._generated()),
                     SOURCE_CURRENT: self._current() is not None}
        for key, button in self.source_buttons.items():
            button.setEnabled(available[key])
        wanted = prefer if prefer is not None and available.get(prefer) else None
        if wanted is None and not any(b.isChecked() and b.isEnabled() for b in self.source_buttons.values()):
            wanted = next(k for k in (SOURCE_SELECTION, SOURCE_BATCH, SOURCE_FILE) if available[k])
        if wanted is not None:
            self.source_buttons[wanted].setChecked(True)
        self._on_options_changed()

    def _library_sources(self) -> list:
        sources = []
        for item in self._selection():
            if item.virtual:
                continue
            if item.kind == Kind.ENTRY:
                sources.append((item.path, item.index))
            elif item.kind == Kind.FILE:
                sources.append((item.path, None))
        return sources

    def source_key(self) -> str:
        return next((k for k, b in self.source_buttons.items() if b.isChecked()), SOURCE_FILE)

    def sources(self) -> list:
        key = self.source_key()
        if key == SOURCE_SELECTION:
            return self._library_sources()
        if key == SOURCE_FILE:
            path = self.source_file.text().strip()
            return [(Path(path), None)] if path else []
        if key == SOURCE_BATCH:
            return [f.copy() for f in self._generated()]
        current = self._current()
        return [current.copy()] if current is not None else []

    def script(self) -> tuple[str, str]:
        """(code, name) of the chosen script."""
        template: T.Template | None = self.script_box.currentData()
        if template is not None:
            return template.code, template.name
        editor = self._editor()
        return editor.editor.text(), editor.script_name

    def spec(self) -> BatchSpec:
        code, name = self.script()
        editor = self._editor()
        values = editor.live.values_for_run() if self.values_box.currentIndex() == 0 and self.script_box.currentIndex() == 0 else {}
        return BatchSpec(code, name, values, random.getrandbits(32), self.seeds_box.currentData(), self.names_box.currentText() or "{name}",
                         self.errors_box.currentIndex() == 1)

    def _problems(self) -> list[str]:
        problems = []
        if not self.sources():
            problems.append("Choose the fractals to run the script on")
        path = self.output_path.text().strip()
        if not path:
            problems.append("Choose the file the results are added to")
        else:
            try:
                fmt = fractal_format_for(path)
                if not fmt.can_append:
                    problems.append(f"{fmt.name} files cannot be written")
            except ValueError as exc:
                problems.append(str(exc))
            if self.source_key() == SOURCE_FILE and Path(path) == Path(self.source_file.text().strip()):
                problems.append("The results cannot go into the file they are read from")
        return problems

    def _on_options_changed(self, *_args) -> None:
        self._persist()
        problems = self._problems()
        idle = self.job is None
        self.start_button.setEnabled(not problems and idle)
        self.start_button.setToolTip("\n".join(problems))
        if problems:
            self.summary.setText(colored_html("; ".join(problems), "error"))
        else:
            count = len(self.sources())
            self.summary.setText(f"Runs '{self.script()[1]}' on {count} source{'s' if count != 1 else ''}; the results are added to "
                                 f"{Path(self.output_path.text()).name}. The fractals the script reads are never changed.")

    def _browse_source(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Fractals to run the script on", self.source_file.text(), open_dialog_filter())
        if path:
            self.source_file.setText(path)
            self.source_buttons[SOURCE_FILE].setChecked(True)

    def _browse_output(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Add the results to", self.output_path.text(), save_dialog_filter(),
                                              options=QFileDialog.Option.DontConfirmOverwrite)
        if path:
            self.output_path.setText(path if Path(path).suffix else path + ".fa")

    # --- running --------------------------------------------------------------------------------------------------------
    def start(self, ask_overwrite: bool = True) -> None:
        if self.job is not None or self._problems():
            return
        output = Path(self.output_path.text().strip())
        self._note_write(output)
        self._launch(ScriptBatchJob(self.spec(), self.sources(), output, self), BatchProgress(phase="Starting"))

    def _on_progress(self, progress: BatchProgress) -> None:
        if progress.item is not None and progress.item.ok:
            self._note_write(Path(self.output_path.text().strip()))
        self.progress_panel.show_progress(progress)

    def _on_succeeded(self, outcome: BatchOutcome) -> None:
        self.last_outcome = outcome
        self._showing_result = True
        self.progress_panel.show_outcome(outcome)


__all__ = ["ScriptBatchWindow", "ScriptBatchJob", "BatchProgressPanel", "BatchOutcome", "BatchProgress"]
