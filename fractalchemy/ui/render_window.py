"""The Render Image window: options on the left, preview and progress on the right, Start / Pause / Stop below.

Opened from *Windows ▸ Render Image* or the toolbar. It is a tool window of the main window:
closing it hides it, and a render keeps going — the job runs on its own thread (`FinalRenderJob`)
with a snapshot of the flame taken when Start was pressed, so the main window is free to open
and edit another fractal meanwhile. Settings persist in QSettings; the destination defaults to
the last folder used and the flame's name.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QSettings, QStandardPaths, Qt, QTimer
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QScrollArea, QSplitter,
                               QVBoxLayout, QWidget)

from ..render.final_engine import PHASE_CANCELLED, PHASE_DONE, FinalProgress
from ..render.final_service import FinalOutcome, FinalRenderJob
from ..render.final_settings import ENGINE_CPU, FinalRenderSettings, describe_plan, plan_tiles
from ..render.gpu_engine import gpu_available
from ..render.output import output_format, size_problem
from ..widgets.icons import render_icon
from .fractal_document import FractalDocument
from .render_output_panel import OutputPanel
from .render_quality_panel import QualityPanel
from .render_size_panel import SizePanel
from .render_progress import RenderProgressPanel, format_rate, format_seconds

WINDOW_TITLE = "Render Image"
SETTINGS_KEY = "final_render/settings"
FOLDER_KEY = "final_render/folder"
RateHint = Callable[[], tuple[str, float] | None]


class RenderWindow(QMainWindow):
    """Non-modal render dialog bound to the main window's document."""

    def __init__(self, document: FractalDocument, parent: QWidget | None = None, settings: QSettings | None = None,
                 rate_hint: RateHint | None = None):
        """Args:
            document: The fractal to render (its flame is copied when Start is pressed).
            parent: Owning window; when given this becomes a child top-level window.
            settings: Where options persist (the application's store by default).
            rate_hint: Returns (engine name, samples per second) of the preview engine, for the time estimate.
        """
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowIcon(render_icon())
        self.document = document
        self._settings = settings if settings is not None else QSettings()
        self._rate_hint = rate_hint
        self._measured: dict[str, float] = {}
        self.job: FinalRenderJob | None = None
        self.last_outcome: FinalOutcome | None = None
        self._showing_result = False
        self._job_started = 0.0
        self._clock = QTimer(self, interval=1000)
        self._clock.timeout.connect(self._tick)
        self.size_panel = SizePanel(self)
        self.quality_panel = QualityPanel(self)
        self.output_panel = OutputPanel(self)
        self.plan_label = QLabel(self)
        self.estimate_label = QLabel(self)
        self.progress_panel = RenderProgressPanel(self)
        self.start_button = QPushButton("Start render", self)
        self.pause_button = QPushButton("Pause", self)
        self.stop_button = QPushButton("Stop", self)
        self.close_button = QPushButton("Close", self)
        self._build()
        self._load()
        self._connect()
        self._on_flame_replaced()

    # --- construction -------------------------------------------------------------------
    def _build(self) -> None:
        for label in (self.plan_label, self.estimate_label):
            label.setWordWrap(True)
        options = QWidget(self)
        column = QVBoxLayout(options)
        column.addWidget(self.size_panel)
        column.addWidget(self.quality_panel)
        column.addWidget(self.output_panel)
        column.addWidget(self.plan_label)
        column.addWidget(self.estimate_label)
        column.addStretch(1)
        scroll = QScrollArea(self)
        scroll.setWidget(options)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(520)
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(scroll)
        splitter.addWidget(self.progress_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        self.start_button.setDefault(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        for button in (self.start_button, self.pause_button, self.stop_button, self.close_button):
            buttons.addWidget(button)
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.addWidget(splitter, 1)
        layout.addLayout(buttons)
        self.setCentralWidget(central)
        self.resize(1100, 720)

    def _connect(self) -> None:
        self.size_panel.size_changed.connect(self._on_options_changed)
        self.quality_panel.changed.connect(self._on_options_changed)
        self.output_panel.changed.connect(self._on_options_changed)
        self.document.flame_replaced.connect(self._on_flame_replaced)
        self.document.flame_renamed.connect(self._on_flame_replaced)
        self.document.image_size_changed.connect(self._on_image_size_changed)
        self.start_button.clicked.connect(lambda: self.start())
        self.pause_button.clicked.connect(self.toggle_pause)
        self.stop_button.clicked.connect(self.stop)
        self.close_button.clicked.connect(self.close)

    def _load(self) -> None:
        stored = self._settings.value(SETTINGS_KEY, "")
        settings = FinalRenderSettings()
        if stored:
            try:
                settings = FinalRenderSettings.from_dict(json.loads(stored))
            except (TypeError, ValueError):
                pass
        self.size_panel.set_size(settings.width, settings.height)
        self.quality_panel.apply(settings)
        self.output_panel.apply(settings)

    # --- settings ------------------------------------------------------------------------
    def current_settings(self) -> FinalRenderSettings:
        """What the panels currently describe."""
        s = FinalRenderSettings().with_size(*self.size_panel.size())
        s = self.quality_panel.read(s)
        return self.output_panel.read(s)

    def _persist(self) -> None:
        s = self.current_settings()
        self._settings.setValue(SETTINGS_KEY, json.dumps(s.to_dict()))
        if s.output_path:
            self._settings.setValue(FOLDER_KEY, str(Path(s.output_path).parent))

    def _uses_gpu(self, s: FinalRenderSettings) -> bool:
        return s.engine != ENGINE_CPU and gpu_available()[0]

    # --- document -------------------------------------------------------------------------
    def _on_flame_replaced(self) -> None:
        flame = self.document.flame
        self.setWindowTitle(f"{WINDOW_TITLE} — {flame.name}" if flame else WINDOW_TITLE)
        self.size_panel.set_preview_size(*self.document.image_size)
        if flame is not None:
            self.output_panel.set_path(self._default_path(flame.name))
        self._on_options_changed()

    def _on_image_size_changed(self) -> None:
        self.size_panel.set_preview_size(*self.document.image_size)

    def _default_path(self, name: str) -> str:
        current = self.output_panel.path.text().strip()
        folder = Path(current).parent if current else Path(self._settings.value(
            FOLDER_KEY, QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation) or str(Path.home())))
        fmt = output_format(self.output_panel.format_box.currentData())
        stem = re.sub(r'[\\/:*?"<>|]+', "_", name).strip() or "fractal"
        return str(folder / f"{stem}{fmt.extension}")

    # --- plan / estimate -------------------------------------------------------------------
    def _on_options_changed(self, *_args) -> None:
        s = self.current_settings()
        self._persist()
        problems = s.problems()
        fmt = output_format(s.output_format)
        size_issue = size_problem(fmt, s.width, s.height)
        if size_issue:
            problems.append(size_issue)
        if self.document.flame is None:
            problems.append("No fractal is loaded")
        self.start_button.setEnabled(not problems and self.job is None)
        self.start_button.setToolTip("\n".join(problems))
        if problems and self.job is None:
            self.plan_label.setText('<span style="color:#c0392b">' + "; ".join(problems) + "</span>")
            self.estimate_label.setText("")
            return
        plan = plan_tiles(s, gpu=self._uses_gpu(s))
        self.plan_label.setText(describe_plan(s, plan))
        self.estimate_label.setText(self._estimate_text(s, plan.count))
        if self.job is None and not self._showing_result:
            self.progress_panel.show_idle(self._estimate_short(s, plan.count))

    def _rate_for(self, s: FinalRenderSettings) -> tuple[str, float] | None:
        """(source description, samples/s) for the engine this render will use, from measurements if any."""
        kind = "GPU" if self._uses_gpu(s) else "CPU"
        if kind in self._measured:
            return f"the last {kind} render's measured speed", self._measured[kind]
        hint = self._rate_hint() if self._rate_hint is not None else None
        if hint and hint[1] > 0 and hint[0].startswith(kind):
            return "the preview's measured speed", hint[1]
        return None

    def _estimate_text(self, s: FinalRenderSettings, tiles: int) -> str:
        rate = self._rate_for(s)
        total = s.samples_per_tile * tiles
        if rate is None:
            return f"{total / 1e9:.2f} G samples to run. Time unknown until an engine has measured its speed."
        return (f"{total / 1e9:.2f} G samples to run — roughly {format_seconds(total / rate[1])} at {rate[0]} "
                f"({format_rate(rate[1])}), plus filtering.")

    def _estimate_short(self, s: FinalRenderSettings, tiles: int) -> str:
        rate = self._rate_for(s)
        return f"≈ {format_seconds(s.samples_per_tile * tiles / rate[1])}" if rate else ""

    # --- rendering ------------------------------------------------------------------------
    @property
    def rendering(self) -> bool:
        """True while a job runs."""
        return self.job is not None

    def start(self, ask_overwrite: bool = True) -> None:
        """Snapshot the flame and settings and start the render thread.

        Args:
            ask_overwrite: Confirm before replacing an existing file (tests pass False).
        """
        flame = self.document.flame
        if flame is None or self.job is not None:
            return
        s = self.current_settings()
        problems = s.problems()
        if problems:
            QMessageBox.warning(self, WINDOW_TITLE, "\n".join(problems))
            return
        if ask_overwrite and Path(s.output_path).exists():
            answer = QMessageBox.question(self, WINDOW_TITLE, f"{Path(s.output_path).name} already exists. Overwrite it?",
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
        self._persist()
        self.last_outcome = None
        self.job = FinalRenderJob(flame, s, self)
        self.job.progressed.connect(self._on_progress)
        self.job.succeeded.connect(self._on_succeeded)
        self.job.failed.connect(self._on_failed)
        self.job.finished.connect(self._on_thread_finished)
        self._set_running(True)
        self._showing_result = False
        self.progress_panel.clear_result()
        self.progress_panel.show_progress(FinalProgress(phase="Starting the engine", tiles=0, engine=""))
        self._job_started = time.perf_counter()
        self._clock.start()
        self.job.start()

    def _tick(self) -> None:
        """Keep the elapsed time moving between engine reports (engine start-up, long batches)."""
        if self.job is not None and not self.job.paused:
            self.progress_panel.show_elapsed(time.perf_counter() - self._job_started - self.job.control.paused_seconds)

    def toggle_pause(self) -> None:
        """Pause / resume the running render."""
        if self.job is None:
            return
        if self.job.paused:
            self.job.resume()
        else:
            self.job.pause()
        self.pause_button.setText("Resume" if self.job.paused else "Pause")
        self.progress_panel.show_paused(self.job.paused)

    def stop(self) -> None:
        """Stop the running render (what is done is saved if 'Save incomplete renders' is on)."""
        if self.job is not None:
            self.job.cancel()
            self.stop_button.setEnabled(False)

    def wait_for_job(self, timeout_ms: int = 30000) -> None:
        """Block until the job's thread has exited (used on quit and by tests)."""
        if self.job is not None:
            self.job.wait(timeout_ms)

    def _set_running(self, running: bool) -> None:
        for panel in (self.size_panel, self.quality_panel, self.output_panel):
            panel.setEnabled(not running)
        self.start_button.setEnabled(not running)
        self.pause_button.setEnabled(running)
        self.pause_button.setText("Pause")
        self.stop_button.setEnabled(running)

    def _on_progress(self, progress: FinalProgress) -> None:
        if progress.phase in (PHASE_DONE, PHASE_CANCELLED) and progress.rate > 0:
            self._measured["GPU" if progress.engine.startswith("GPU") else "CPU"] = progress.rate
        self.progress_panel.show_progress(progress)

    def _on_succeeded(self, outcome: FinalOutcome) -> None:
        self.last_outcome = outcome
        self._showing_result = True
        self.progress_panel.show_outcome(outcome)

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

    # --- window ---------------------------------------------------------------------------
    def bring_to_front(self) -> None:
        """Show, raise and focus the window."""
        self.show()
        self.raise_()
        self.activateWindow()

    def confirm_quit(self) -> bool:
        """Ask before quitting with a render running; stops it if the user agrees. False = keep running."""
        if self.job is None:
            return True
        answer = QMessageBox.question(self, WINDOW_TITLE, "A render is still running. Stop it and quit?",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return False
        self.job.cancel()
        self.wait_for_job()
        return True

    def closeEvent(self, event) -> None:
        """Closing hides the window; a running render carries on (a standalone window stops it first)."""
        if self.parent() is not None:
            event.ignore()
            self.hide()
            return
        if self.job is not None:
            self.job.cancel()
            self.wait_for_job()
        super().closeEvent(event)


__all__ = ["RenderWindow"]
