"""What the Render Image and Render Animation windows share: a job thread driven by Start / Pause / Stop.

`JobWindowBase` owns the layout skeleton (option panels in a scroll area on the left, a progress
panel on the right, the four buttons below), the job's life cycle (launch, pause / resume, stop,
the elapsed-time clock, tidy-up when the thread exits) and the window behaviour (closing hides a
child window while its job carries on; quitting asks first). Subclasses supply the panels, build
the job and show its progress and outcome.
"""

from __future__ import annotations

import time

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QMessageBox, QPushButton, QScrollArea, QSplitter, QVBoxLayout, QWidget

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
    def _build_layout(self, progress_panel: QWidget, size: tuple[int, int]) -> None:
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
        scroll.setMinimumWidth(OPTIONS_MIN_WIDTH)
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(scroll)
        splitter.addWidget(progress_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
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
    def rendering(self) -> bool:
        """True while a job runs."""
        return self.job is not None

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
        self._set_running(True)
        self._showing_result = False
        self.progress_panel.clear_result()
        self.progress_panel.show_progress(first_progress)
        self._job_started = time.perf_counter()
        self._clock.start()
        job.start()

    def toggle_pause(self) -> None:
        """Pause / resume the running job."""
        if self.job is None:
            return
        if self.job.paused:
            self.job.resume()
        else:
            self.job.pause()
        self.pause_button.setText("Resume" if self.job.paused else "Pause")
        self.progress_panel.show_paused(self.job.paused)

    def stop(self) -> None:
        """Stop the running job (what it keeps is up to the job's settings)."""
        if self.job is not None:
            self.job.cancel()
            self.stop_button.setEnabled(False)

    def wait_for_job(self, timeout_ms: int = 60000) -> None:
        """Block until the job's thread has exited (used on quit and by tests)."""
        if self.job is not None:
            self.job.wait(timeout_ms)

    def _tick(self) -> None:
        """Keep the elapsed time moving between the job's reports."""
        if self.job is not None and not self.job.paused:
            self.progress_panel.show_elapsed(time.perf_counter() - self._job_started - self.job.control.paused_seconds)

    def _set_running(self, running: bool) -> None:
        for panel in self._option_panels():
            panel.setEnabled(not running)
        self.start_button.setEnabled(not running)
        self.pause_button.setEnabled(running)
        self.pause_button.setText("Pause")
        self.stop_button.setEnabled(running)

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
        self._set_running(False)
        self._on_options_changed()

    def _on_options_changed(self, *_args) -> None:
        """Re-validate the settings and refresh the plan / estimate (also after a job ends)."""
        raise NotImplementedError

    # --- window ----------------------------------------------------------------------------------------------------
    def bring_to_front(self) -> None:
        """Show, raise and focus the window."""
        self.show()
        self.raise_()
        self.activateWindow()

    def confirm_quit(self) -> bool:
        """Ask before quitting with a job running; stops it if the user agrees. False = keep running."""
        if self.job is None:
            return True
        answer = QMessageBox.question(self, self.title, self.quit_question,
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return False
        self.job.cancel()
        self.wait_for_job()
        return True

    def closeEvent(self, event) -> None:
        """Closing hides a child window (its job carries on); a standalone window stops the job first."""
        if self.parent() is not None:
            event.ignore()
            self.hide()
            return
        if self.job is not None:
            self.job.cancel()
            self.wait_for_job()
        super().closeEvent(event)


__all__ = ["JobWindowBase"]
