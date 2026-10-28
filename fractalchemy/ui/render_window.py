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
from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths
from PySide6.QtWidgets import QLabel, QMessageBox, QWidget

from ..render.final_engine import PHASE_CANCELLED, PHASE_DONE, FinalProgress
from ..render.final_service import FinalOutcome, FinalRenderJob
from ..render.estimate import RateHint, RenderEstimate, engine_kind
from ..render.final_settings import FinalRenderSettings, describe_plan, plan_tiles
from ..render.gpu_engine import gpu_available
from ..render.output import output_format, size_problem
from ..widgets.icons import render_icon
from .fractal_document import FractalDocument
from .job_window import JobWindowBase
from .render_output_panel import OutputPanel
from .render_progress import RenderProgressPanel
from .render_quality_panel import QualityPanel
from .render_size_panel import SizePanel

WINDOW_TITLE = "Render Image"
SETTINGS_KEY = "final_render/settings"
FOLDER_KEY = "final_render/folder"


class RenderWindow(JobWindowBase):
    """Non-modal render dialog bound to the main window's document."""
    title = WINDOW_TITLE
    quit_question = "A render is still running. Stop it and quit?"

    def __init__(self, document: FractalDocument, parent: QWidget | None = None, settings: QSettings | None = None,
                 rate_hint: RateHint | None = None):
        """Args:
            document: The fractal to render (its flame is copied when Start is pressed).
            parent: Owning window; when given this becomes a child top-level window.
            settings: Where options persist (the application's store by default).
            rate_hint: Returns (engine name, samples per second) of the preview engine, for the time estimate.
        """
        super().__init__(parent, settings)
        self.setWindowIcon(render_icon())
        self.document = document
        self._rate_hint = rate_hint
        self._estimate = RenderEstimate()
        self.job: FinalRenderJob | None = None
        self.last_outcome: FinalOutcome | None = None
        self.size_panel = SizePanel(self)
        self.quality_panel = QualityPanel(self)
        self.output_panel = OutputPanel(self)
        self.plan_label = QLabel(self)
        self.estimate_label = QLabel(self)
        self.progress_panel = RenderProgressPanel(self)
        for label in (self.plan_label, self.estimate_label):
            label.setWordWrap(True)
        self._build_layout(self.progress_panel, (1100, 720))
        self._load()
        self._connect()
        self._on_flame_replaced()

    # --- construction -------------------------------------------------------------------
    def _option_widgets(self) -> list[QWidget]:
        return [self.size_panel, self.quality_panel, self.output_panel, self.plan_label, self.estimate_label]

    def _option_panels(self) -> list[QWidget]:
        return [self.size_panel, self.quality_panel, self.output_panel]

    def _connect(self) -> None:
        self.size_panel.size_changed.connect(self._on_options_changed)
        self.quality_panel.changed.connect(self._on_options_changed)
        self.output_panel.changed.connect(self._on_options_changed)
        self.document.flame_replaced.connect(self._on_flame_replaced)
        self.document.flame_renamed.connect(self._on_flame_replaced)
        self.document.image_size_changed.connect(self._on_image_size_changed)

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

    def _engine_kind(self, s: FinalRenderSettings) -> str:
        return engine_kind(s, gpu_available()[0])

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
    def _problems(self, s: FinalRenderSettings) -> list[str]:
        """Everything that prevents a render: invalid settings, a size the format cannot hold, no fractal."""
        problems = s.problems()
        size_issue = size_problem(output_format(s.output_format), s.width, s.height)
        if size_issue:
            problems.append(size_issue)
        if self.document.flame is None:
            problems.append("No fractal is loaded")
        return problems

    def _on_options_changed(self, *_args) -> None:
        s = self.current_settings()
        self._persist()
        problems = self._problems(s)
        self.start_button.setEnabled(not problems and self.job is None)
        self.start_button.setToolTip("\n".join(problems))
        if problems and self.job is None:
            self.plan_label.setText('<span style="color:#c0392b">' + "; ".join(problems) + "</span>")
            self.estimate_label.setText("")
            return
        kind = self._engine_kind(s)
        plan = plan_tiles(s, gpu=kind == "gpu")
        hint = self._rate_hint() if self._rate_hint is not None else None
        self.plan_label.setText(describe_plan(s, plan))
        self.estimate_label.setText(self._estimate.describe(s, plan.count, kind, hint))
        if self.job is None and not self._showing_result:
            self.progress_panel.show_idle(self._estimate.short(s, plan.count, kind, hint))

    # --- rendering ------------------------------------------------------------------------
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
        self._launch(FinalRenderJob(flame, s, self, source=self._source_text()),
                     FinalProgress(phase="Starting the engine", tiles=0, engine=""))

    def _source_text(self) -> str:
        path = self.document.source_path
        return f"{path} (entry {self.document.source_index + 1})" if path else ""

    def _on_progress(self, progress: FinalProgress) -> None:
        if progress.phase in (PHASE_DONE, PHASE_CANCELLED):
            self._estimate.record(progress.engine_kind, progress.rate)
        self.progress_panel.show_progress(progress)

    def _on_succeeded(self, outcome: FinalOutcome) -> None:
        self.last_outcome = outcome
        self._showing_result = True
        self.progress_panel.show_outcome(outcome)



__all__ = ["RenderWindow"]
