"""What the Render Image and Render Animation windows share: a job thread driven by Start / Pause / Stop.

`JobWindowBase` owns the layout skeleton (option panels in a scroll area on the left, a progress
panel on the right, the four buttons below), the job's life cycle (launch, pause / resume, stop,
the elapsed-time clock, tidy-up when the thread exits) and the window behaviour (closing hides a
child window while its job carries on; quitting asks first). Subclasses supply the panels, build
the job and show its progress and outcome.

The life cycle is the explicit `machines.JOB` machine — *idle → running ⇄ paused → stopping → idle* — in
`self.machine`; the buttons and the option panels are derived from its state (`_refresh_controls`), so they can
never offer what the state does not allow (pausing a job that is stopping used to hang its thread).
"""

from __future__ import annotations

import time

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QMessageBox, QPushButton, QScrollArea, QSplitter, QVBoxLayout, QWidget

from ..machines import JOB, JobState, Transition
from ..widgets.windows import bring_to_front

OPTIONS_MIN_WIDTH = 520


class JobWindowBase(QMainWindow):
    """A non-modal window running one background job at a time (see the module docstring).

    Subclasses implement `_option_widgets()` (the panels, top to bottom, disabled while a job runs),
    `_create_job()` (a started-later thread with `progressed` / `succeeded` / `failed` / `finished`
    signals and `pause` / `resume` / `cancel` / `paused` / `control`), `_on_progress`,
    `_on_succeeded` and `_on_options_changed`, and set `title` and `quit_question`.
    """
    title = "Render"
    quit_question = "A render is still running. Stop it and quit?"

    def __init__(self, parent: QWidget | None = None, settings: QSettings | None = None):
        """Args:
            parent: Owning window; when given this becomes a child top-level window that hides on close.
            settings: Where options persist (the application's store by default).
        """
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle(self.title)
        self._settings = settings if settings is not None else QSettings()
        self.job = None
        self.machine = JOB.new(self.title)
        self.machine.on_change(self._on_state_changed)
        self.last_outcome = None
        self._showing_result = False
        self._job_started = 0.0
        self._clock = QTimer(self, interval=1000)
        self._clock.timeout.connect(self._tick)
        self.start_button = QPushButton("Start render", self)
        self.pause_button = QPushButton("Pause", self)
        self.stop_button = QPushButton("Stop", self)
        self.close_button = QPushButton("Close", self)
        self.start_button.setDefault(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.start_button.clicked.connect(lambda: self.start())
        self.pause_button.clicked.connect(self.toggle_pause)
        self.stop_button.clicked.connect(self.stop)
        self.close_button.clicked.connect(self.close)

    # --- layout ------------------------------------------------------------------------------------------------
    def _build_layout(self, progress_panel: QWidget, size: tuple[int, int], options_width: int = OPTIONS_MIN_WIDTH) -> None:
        """Options (from `_option_widgets`) on the left, `progress_panel` on the right, the buttons below."""
        options = QWidget(self)
        column = QVBoxLayout(options)
        for widget in self._option_widgets():
            column.addWidget(widget)
        column.addStretch(1)
        scroll = QScrollArea(self)
        scroll.setWidget(options)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(options_width)
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(scroll)
        splitter.addWidget(progress_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([options_width, max(300, size[0] - options_width)])
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        for button in (self.start_button, self.pause_button, self.stop_button, self.close_button):
            buttons.addWidget(button)
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.addWidget(splitter, 1)
        layout.addLayout(buttons)
        self.setCentralWidget(central)
        self.resize(*size)

    def _option_widgets(self) -> list[QWidget]:
        """The option panels and labels, top to bottom (panels are disabled while a job runs)."""
        raise NotImplementedError

    def _option_panels(self) -> list[QWidget]:
        """The widgets disabled while a job runs (the option widgets by default)."""
        return self._option_widgets()

    # --- the job --------------------------------------------------------------------------------------------------
    @property
    def job_state(self) -> JobState:
        """Where the job's life cycle is (`idle`, `running`, `paused`, `stopping`)."""
        return self.machine.state

    @property
    def rendering(self) -> bool:
        """True while a job runs (paused or stopping included)."""
        return self.machine.state != JobState.IDLE

    def start(self, ask_overwrite: bool = True) -> None:
        """Validate, snapshot and launch a job (subclasses decide what to ask; `_launch` does the rest)."""
        raise NotImplementedError

    def _launch(self, job, first_progress) -> None:
        """Connect and start `job`, switching the window to its running state."""
        self.last_outcome = None
        self.job = job
        job.progressed.connect(self._on_progress)
        job.succeeded.connect(self._on_succeeded)
        job.failed.connect(self._on_failed)
        job.finished.connect(self._on_thread_finished)
        job.progressed.connect(lambda _progress: self._show_state_note())   # after the subclass's own display
        self.machine.fire("start")
        self._showing_result = False
        self.progress_panel.clear_result()
        self.progress_panel.show_progress(first_progress)
        self._job_started = time.perf_counter()
        self._clock.start()
        job.start()

    def toggle_pause(self) -> None:
        """Pause the running job, or resume the paused one (nothing in the other states)."""
        if self.machine.can("pause") and self._can_pause_now():
            self.job.pause()
            self.machine.fire("pause")
        elif self.machine.can("resume"):
            self.job.resume()
            self.machine.fire("resume")

    def stop(self) -> None:
        """Stop the running or paused job (what it keeps is up to the job's settings)."""
        if self.machine.can("stop"):
            self.job.cancel()
            self.machine.fire("stop")

    def _can_pause_now(self) -> bool:
        """Whether the running job can be paused at this moment (a subclass may say no: ffmpeg cannot be paused)."""
        return True

    def wait_for_job(self, timeout_ms: int = 60000) -> None:
        """Block until the job's thread has exited (used on quit and by tests)."""
        if self.job is not None:
            self.job.wait(timeout_ms)

    def _tick(self) -> None:
        """Keep the elapsed time moving between the job's reports."""
        if self.job is not None and not self.job.paused:
            self.progress_panel.show_elapsed(time.perf_counter() - self._job_started - self.job.control.paused_seconds)

    def _on_state_changed(self, _step: Transition) -> None:
        self._refresh_controls()
        self._show_state_note()

    def _refresh_controls(self) -> None:
        """Buttons and option panels from the job's state (and `_can_pause_now`)."""
        idle = self.machine.state == JobState.IDLE
        for panel in self._option_panels():
            panel.setEnabled(idle)
        self.start_button.setEnabled(idle)
        self.pause_button.setEnabled(self.machine.can("resume") or (self.machine.can("pause") and self._can_pause_now()))
        self.pause_button.setText("Resume" if self.machine.state == JobState.PAUSED else "Pause")
        self.stop_button.setEnabled(self.machine.can("stop"))

    def _show_state_note(self) -> None:
        """*(paused)* / *(stopping)* after the progress panel's phase line."""
        state = self.machine.state
        self.progress_panel.show_note("paused" if state == JobState.PAUSED else "stopping" if state == JobState.STOPPING else "")

    def _on_progress(self, progress) -> None:
        raise NotImplementedError

    def _on_succeeded(self, outcome) -> None:
        raise NotImplementedError

    def _on_failed(self, message: str) -> None:
        self._showing_result = True
        self.progress_panel.show_failure(message)

    def _on_thread_finished(self) -> None:
        job = self.job
        self.job = None
        self._clock.stop()
        if job is not None:
            job.deleteLater()
        self.machine.fire("finished")
        self._on_options_changed()

    def _on_options_changed(self, *_args) -> None:
        """Re-validate the settings and refresh the plan / estimate (also after a job ends)."""
        raise NotImplementedError

    # --- window ----------------------------------------------------------------------------------------------------
    def bring_to_front(self) -> None:
        """Show, raise and focus the window."""
        bring_to_front(self)

    def confirm_quit(self) -> bool:
        """Ask before quitting with a job running; stops it if the user agrees. False = keep running."""
        if not self.rendering:
            return True
        answer = QMessageBox.question(self, self.title, self.quit_question,
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return False
        self.stop()
        self.wait_for_job()
        return True

    def closeEvent(self, event) -> None:
        """Closing hides a child window (its job carries on); a standalone window stops the job first."""
        if self.parent() is not None:
            event.ignore()
            self.hide()
            return
        if self.rendering:
            self.stop()
            self.wait_for_job()
        super().closeEvent(event)


__all__ = ["JobWindowBase"]
