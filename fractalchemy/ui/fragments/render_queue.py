"""The Render Queue window: several renders lined up and run one after another on their own thread.

*Add to queue* in the Render Fragment window (or the queue's own button) snapshots the current tab with the render
settings shown there — the program, the parameters, the plan — as a `FragRenderInput`; the queue runs the entries
in order with one `FragRenderJob` at a time, showing the running job's progress in the usual panel and each entry's
state (waiting / rendering / done / failed / stopped) in the list. Entries can be removed while waiting; *Stop*
ends the running job and leaves the rest waiting; closing hides the window while the queue carries on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMainWindow, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from ...fragments.gl.final_job import FragOutcome, FragRenderInput, FragRenderJob
from ...render.final_engine import FinalProgress
from ...machines import RENDER_QUEUE, QueueState
from ..render_progress import RenderProgressPanel

WAITING, RENDERING, DONE, FAILED, STOPPED = "waiting", "rendering", "done", "failed", "stopped"
COLUMNS = ("Fragment", "Plan", "Output", "State")


@dataclass
class QueueEntry:
    """One queued render."""
    inputs: FragRenderInput
    state: str = WAITING
    outcome: FragOutcome | None = None
    message: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return self.inputs.name + (f" [{self.inputs.preset}]" if self.inputs.preset else "")


class RenderQueueWindow(QMainWindow):
    """The queue (see the module docstring).

    Signals:
        add_requested(): The *Add current tab* button — the owner snapshots the current tab and calls `add`.
        entry_finished(object): A `QueueEntry` reached `done` / `failed` / `stopped`.
    """
    add_requested = Signal()
    entry_finished = Signal(object)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("Render Queue")
        self.entries: list[QueueEntry] = []
        self.job: FragRenderJob | None = None
        self._current: QueueEntry | None = None
        self.machine = RENDER_QUEUE.new("render queue")     # idle → running → stopping → idle (machines.RENDER_QUEUE)
        self.table = QTableWidget(0, len(COLUMNS), self)
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().hide()
        self.progress_panel = RenderProgressPanel(self)
        self.add_button = QPushButton("Add current tab", self)
        self.add_button.setToolTip("Queue the current tab with the Render Fragment window's settings")
        self.remove_button = QPushButton("Remove", self)
        self.clear_button = QPushButton("Clear finished", self)
        self.start_button = QPushButton("Start queue", self)
        self.stop_button = QPushButton("Stop", self)
        self.stop_button.setEnabled(False)
        self.summary = QLabel(self)
        buttons = QHBoxLayout()
        for button in (self.add_button, self.remove_button, self.clear_button):
            buttons.addWidget(button)
        buttons.addStretch(1)
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.stop_button)
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.addWidget(self.summary)
        layout.addWidget(self.table, 2)
        layout.addWidget(self.progress_panel, 3)
        layout.addLayout(buttons)
        self.setCentralWidget(central)
        self.resize(900, 700)
        self.add_button.clicked.connect(self.add_requested)
        self.remove_button.clicked.connect(self.remove_selected)
        self.clear_button.clicked.connect(self.clear_finished)
        self.start_button.clicked.connect(self.start)
        self.stop_button.clicked.connect(self.stop)
        self._refresh()

    # --- entries ------------------------------------------------------------------------------------------------------
    def add(self, inputs: FragRenderInput) -> QueueEntry:
        """Queue a snapshot (and start rendering it if the queue is running)."""
        entry = QueueEntry(inputs)
        self.entries.append(entry)
        self._refresh()
        if self.machine.state == QueueState.RUNNING and self.job is None:
            self._next()
        return entry

    def remove_selected(self) -> None:
        rows = sorted({index.row() for index in self.table.selectedIndexes()}, reverse=True)
        for row in rows:
            if 0 <= row < len(self.entries) and self.entries[row].state != RENDERING:
                del self.entries[row]
        self._refresh()

    def clear_finished(self) -> None:
        self.entries = [e for e in self.entries if e.state in (WAITING, RENDERING)]
        self._refresh()

    @property
    def waiting(self) -> list[QueueEntry]:
        return [e for e in self.entries if e.state == WAITING]

    # --- running --------------------------------------------------------------------------------------------------------
    @property
    def state(self) -> QueueState:
        """`idle`, `running` or `stopping`."""
        return self.machine.state

    @property
    def running(self) -> bool:
        """True while the queue runs or winds down after Stop."""
        return self.machine.state != QueueState.IDLE

    def start(self) -> None:
        """Run the waiting entries in order (also after Stop, while the cancelled entry winds down)."""
        self.machine.fire("start")
        self._refresh()
        if self.job is None:
            self._next()

    def stop(self) -> None:
        """Cancel the running entry; the rest stay waiting."""
        if not self.machine.can("stop"):
            return
        self.machine.fire("stop")
        if self.job is not None:
            self.job.cancel()
        else:
            self.machine.fire("drained")
        self._refresh()

    def _next(self) -> None:
        waiting = self.waiting
        if self.machine.state == QueueState.STOPPING:
            self.machine.fire("drained")                     # the cancelled entry's thread has ended
        if self.machine.state != QueueState.RUNNING or not waiting:
            self.machine.fire_if("emptied")
            self._refresh()
            return
        entry = waiting[0]
        entry.state = RENDERING
        self._current = entry
        job = FragRenderJob(entry.inputs, self)
        job.progressed.connect(self.progress_panel.show_progress)
        job.succeeded.connect(lambda outcome, e=entry: self._on_succeeded(e, outcome))
        job.failed.connect(lambda message, e=entry: self._on_failed(e, message))
        job.finished.connect(self._on_thread_finished)
        self.job = job
        self.progress_panel.clear_result()
        self.progress_panel.show_progress(FinalProgress(phase=f"Starting {entry.label}", tiles=entry.inputs.settings.tile_count, engine=""))
        self._refresh()
        job.start()

    def _on_succeeded(self, entry: QueueEntry, outcome: FragOutcome) -> None:
        entry.outcome = outcome
        entry.state = DONE if outcome.result.complete else STOPPED
        entry.notes = list(outcome.notes)
        self.progress_panel.show_outcome(outcome)
        self.entry_finished.emit(entry)

    def _on_failed(self, entry: QueueEntry, message: str) -> None:
        entry.state = FAILED
        entry.message = message
        self.progress_panel.show_failure(message)
        self.entry_finished.emit(entry)

    def _on_thread_finished(self) -> None:
        job, self.job = self.job, None
        if job is not None:
            job.deleteLater()
        if self._current is not None and self._current.state == RENDERING:
            self._current.state = STOPPED
        self._current = None
        self._refresh()
        self._next()

    def wait_for_job(self, timeout_ms: int = 60000) -> None:
        if self.job is not None:
            self.job.wait(timeout_ms)

    # --- display --------------------------------------------------------------------------------------------------------
    def _refresh(self) -> None:
        self.table.setRowCount(len(self.entries))
        for row, entry in enumerate(self.entries):
            s = entry.inputs.settings
            size = s.output_size()
            plan = f"{size[0]} × {size[1]}, {s.subframes} subframes" + (f", {len(s.frames(entry.inputs.animation.frames))} frames" if s.animation else "")
            output = "preview" if s.preview else Path(s.output_path).name
            state = entry.state + (f": {entry.message}" if entry.message else "")
            for column, text in enumerate((entry.label, plan, output, state)):
                item = QTableWidgetItem(text)
                if column == 3:
                    item.setToolTip("\n".join(entry.notes) if entry.notes else state)
                self.table.setItem(row, column, item)
        waiting, done = len(self.waiting), sum(1 for e in self.entries if e.state == DONE)
        self.summary.setText(f"{len(self.entries)} entries · {waiting} waiting · {done} done" + (f" · {self.machine.state}" if self.running else ""))
        self.start_button.setEnabled(bool(waiting) and self.machine.state != QueueState.RUNNING)
        self.stop_button.setEnabled(self.machine.can("stop"))

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        if self.parent() is not None:
            event.ignore()
            self.hide()
            return
        self.stop()
        self.wait_for_job()
        super().closeEvent(event)


__all__ = ["RenderQueueWindow", "QueueEntry", "WAITING", "RENDERING", "DONE", "FAILED", "STOPPED"]
