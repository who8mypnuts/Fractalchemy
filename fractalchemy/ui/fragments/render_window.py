"""The Render Fragment window — FragM's *High Resolution and Animation Render* as a Fractalchemy job window.

Options on the left (tiles, quality, animation, output), the progress panel on the right, Start / Pause / Stop /
Close below (`JobWindowBase`). *Start* snapshots the current tab — the program, the parameters, presets, curves and
the clock — and runs a `FragRenderJob` on its own thread with its own OpenGL context, so the editor stays usable;
closing the window hides it while the render carries on. The plan line says what will be drawn and the estimate
extrapolates from the viewport's measured subframe speed. A *preview* render shows the frame in a dialog with *Save*.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QMessageBox, QScrollArea, QVBoxLayout, QWidget

from ...fragments.animation import AnimationSettings
from ...fragments.gl.final import to_display_rgba8, write_frame
from ...fragments.gl.final_job import FragOutcome, FragRenderInput, FragRenderJob
from ...fragments.render_settings import FragFinalSettings, safe_stem
from ...render.final_engine import PHASE_CANCELLED, FinalProgress
from ...render.output import output_format
from ...render.units import format_seconds
from ...widgets.icons import editor_icon
from ...widgets.images import rgba_to_qimage
from ..job_window import JobWindowBase
from ..render_progress import RenderProgressPanel
from .document import FragDocument
from .render_panels import AnimationPanel, FragOutputPanel, QualityPanel, TilesPanel, ViewPanel

WINDOW_TITLE = "Render Fragment"
SETTINGS_KEY = "fragments/render_settings"
FOLDER_KEY = "fragments/render_folder"


class FragRenderWindow(JobWindowBase):
    """Hi-res / animation renders of the current fragment (see the module docstring)."""
    title = WINDOW_TITLE
    quit_question = "A fragment render is still running. Stop it and quit?"

    def __init__(self, document_provider, clock_provider, rate_hint, parent: QWidget | None = None, settings: QSettings | None = None):
        """Args:
            document_provider: Returns the current `FragDocument` (None when no tab is open).
            clock_provider: Returns the window's `AnimationSettings`.
            rate_hint: Returns the viewport's measured subframe draws per second for a pixel count (`(draws_per_s, width, height)` or None).
            parent: Owning window.
            settings: Where options persist.
        """
        super().__init__(parent, settings)
        self.setWindowIcon(editor_icon("render-fragment"))
        self._document_provider = document_provider
        self._clock_provider = clock_provider
        self._rate_hint = rate_hint
        self.job: FragRenderJob | None = None
        self.last_outcome: FragOutcome | None = None
        self.tiles_panel = TilesPanel(self)
        self.quality_panel = QualityPanel(self)
        self.view_panel = ViewPanel(self)
        self.animation_panel = AnimationPanel(self)
        self.output_panel = FragOutputPanel(self)
        self.plan_label = QLabel(self)
        self.estimate_label = QLabel(self)
        for label in (self.plan_label, self.estimate_label):
            label.setWordWrap(True)
        self.progress_panel = RenderProgressPanel(self)
        self._build_layout(self.progress_panel, (1150, 760))
        self._load()
        for panel in (self.tiles_panel, self.quality_panel, self.view_panel, self.animation_panel, self.output_panel):
            panel.changed.connect(self._on_options_changed)
        self._on_options_changed()

    # --- construction ----------------------------------------------------------------------------------------------
    def _option_widgets(self) -> list[QWidget]:
        return [self.tiles_panel, self.quality_panel, self.view_panel, self.animation_panel, self.output_panel, self.plan_label, self.estimate_label]

    def _option_panels(self) -> list[QWidget]:
        return [self.tiles_panel, self.quality_panel, self.view_panel, self.animation_panel, self.output_panel]

    def _load(self) -> None:
        stored = self._settings.value(SETTINGS_KEY, "")
        settings = FragFinalSettings()
        if stored:
            try:
                settings = FragFinalSettings.from_dict(json.loads(stored))
            except (TypeError, ValueError):
                pass
        self.apply_settings(settings)

    def apply_settings(self, settings: FragFinalSettings) -> None:
        """Show `settings` in the panels."""
        self.tiles_panel.apply(settings)
        self.quality_panel.apply(settings)
        self.view_panel.apply(settings)
        self.animation_panel.apply(settings, self._clock_provider())
        self.output_panel.apply(settings)

    def current_settings(self) -> FragFinalSettings:
        s = self.tiles_panel.read(FragFinalSettings())
        s = self.quality_panel.read(s)
        s = self.view_panel.read(s)
        s = self.animation_panel.read(s)
        return self.output_panel.read(s)

    def set_region(self, region: tuple | None, frame_size: tuple[int, int]) -> None:
        """The region of the frame to render (Ctrl+drag on the viewport); the tile takes the region's aspect."""
        self.tiles_panel.set_region(region, frame_size)

    def _persist(self) -> None:
        s = self.current_settings().with_(region=None, tile_range=None)          # a region is a one-off choice, not a habit
        self._settings.setValue(SETTINGS_KEY, json.dumps(s.to_dict()))
        if s.output_path:
            self._settings.setValue(FOLDER_KEY, str(Path(s.output_path).parent))

    # --- the document -----------------------------------------------------------------------------------------------
    def document(self) -> FragDocument | None:
        return self._document_provider()

    def prepare_for(self, document: FragDocument | None, viewport_size: tuple[int, int]) -> None:
        """Called when the window opens: the title, the default file name, the clock, the viewport size for *From viewport*."""
        self._viewport_size = viewport_size
        self.animation_panel.show_clock(self._clock_provider())
        if document is not None:
            self.setWindowTitle(f"{WINDOW_TITLE} — {document.name}")
            if document.metadata.render:
                self.apply_settings(FragFinalSettings.from_dict({**self.current_settings().to_dict(), **document.metadata.render}))
            if not self.output_panel.path_edit.text().strip() or Path(self.output_panel.path_edit.text()).stem in ("fragment", ""):
                self.output_panel.set_path(self._default_path(document.name))
            else:
                current = Path(self.output_panel.path_edit.text())
                self.output_panel.set_path(str(current.with_name(f"{safe_stem(document.name)}{current.suffix}")))
        else:
            self.setWindowTitle(WINDOW_TITLE)
        if not getattr(self, "_from_viewport_connected", False):
            self._from_viewport_connected = True
            self.tiles_panel.from_viewport.clicked.connect(lambda: self.tiles_panel.set_tile_size(*self._viewport_size))
        self._on_options_changed()

    def _default_path(self, name: str) -> str:
        folder = Path(str(self._settings.value(FOLDER_KEY, QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation)
                                                or str(Path.home()))))
        fmt = output_format(str(self.output_panel.format_combo.currentData() or "png"))
        return str(folder / f"{safe_stem(name)}{fmt.extension}")

    # --- plan / estimate ------------------------------------------------------------------------------------------------
    def _on_options_changed(self, *_args) -> None:
        s = self.current_settings()
        self._persist()
        clock = self._clock_provider()
        self.tiles_panel.refresh(s)
        problems = s.problems()
        document = self.document()
        if document is None or document.request() is None:
            problems.append("No built fragment to render")
        self.start_button.setEnabled(not problems and self.job is None)
        self.start_button.setToolTip("\n".join(problems))
        if problems and self.job is None:
            self.plan_label.setText('<span style="color:#c0392b">' + "; ".join(problems) + "</span>")
            self.estimate_label.setText("")
            return
        self.plan_label.setText(s.describe_plan(clock.frames))
        self.animation_panel.show_video_state(s)
        estimate = self._estimate(s, clock)
        self.estimate_label.setText(estimate)
        if self.job is None and not self._showing_result:
            self.progress_panel.show_idle(estimate)

    def _estimate(self, s: FragFinalSettings, clock: AnimationSettings) -> str:
        hint = self._rate_hint() if self._rate_hint is not None else None
        if not hint:
            return "Estimate: render something in the viewport first"
        draws_per_second, width, height = hint
        if draws_per_second <= 0:
            return ""
        pixels_per_second = draws_per_second * width * height
        seconds = s.total_steps(clock.frames) * s.tile_width * s.tile_height / max(1.0, pixels_per_second)
        return f"Estimated {format_seconds(seconds)} at the viewport's speed"

    # --- rendering ------------------------------------------------------------------------------------------------------
    def start(self, ask_overwrite: bool = True) -> None:
        """Snapshot the fragment and launch the job."""
        document = self.document()
        if document is None or document.request() is None or self.job is not None:
            return
        s = self.current_settings()
        problems = s.problems()
        if problems:
            QMessageBox.warning(self, WINDOW_TITLE, "\n".join(problems))
            return
        if ask_overwrite and not s.preview and not s.animation and Path(s.output_path).exists() and not s.unique_name:
            answer = QMessageBox.question(self, WINDOW_TITLE, f"{Path(s.output_path).name} already exists. Overwrite it?",
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
        self._persist()
        document.metadata.render = s.to_dict()
        self._launch(FragRenderJob(self.make_input(document, s), self), FinalProgress(phase="Starting the engine", tiles=s.tile_count, engine=""))

    @staticmethod
    def make_input(document: FragDocument, s: FragFinalSettings) -> FragRenderInput:
        """Snapshot `document` for a job with the plan `s` (the render queue builds its jobs the same way)."""
        return FragRenderInput(document.request(), document.state, document.source, document.text, document.name, document.animation,
                               list(document.easing), s, document.state.to_text(provenance=document.path.name if document.path else "Unnamed"),
                               document.path, document.current_preset)

    def _on_progress(self, progress: FinalProgress) -> None:
        self.progress_panel.show_progress(progress)

    def _on_succeeded(self, outcome: FragOutcome) -> None:
        self.last_outcome = outcome
        self._showing_result = True
        self.progress_panel.show_outcome(outcome)
        job = self.job
        if job is not None and job.inputs.settings.preview and getattr(job, "last_frame", None) is not None:
            self._show_preview(job)

    def _show_preview(self, job: FragRenderJob) -> None:
        """FragM's PREVIEW dialog: the rendered frame with a *Save* button."""
        frame = job.last_frame
        dialog = QDialog(self)
        dialog.setWindowTitle("Preview")
        label = QLabel(dialog)
        label.setPixmap(QPixmap.fromImage(rgba_to_qimage(to_display_rgba8(frame, max_side=4096))))
        scroll = QScrollArea(dialog)
        scroll.setWidget(label)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Close, dialog)
        layout = QVBoxLayout(dialog)
        layout.addWidget(scroll, 1)
        layout.addWidget(buttons)
        buttons.rejected.connect(dialog.reject)

        def save() -> None:
            from PySide6.QtWidgets import QFileDialog
            settings = job.inputs.settings
            chosen, _filter = QFileDialog.getSaveFileName(dialog, "Save preview image", settings.output_path or str(Path.home() / "preview.png"))
            if chosen:
                write_frame(frame, Path(chosen), settings.with_(output_format=output_format_for(chosen, settings.output_format)),
                            job.inputs.settings_text)
                dialog.accept()

        buttons.accepted.connect(save)
        dialog.resize(min(1200, frame.rgba.shape[1] + 40), min(900, frame.rgba.shape[0] + 80))
        dialog.show()
        self._preview_dialog = dialog

    def _on_failed(self, message: str) -> None:
        super()._on_failed(message)
        if message:
            self.progress_panel.show_progress(FinalProgress(phase=PHASE_CANCELLED, engine=""))



def output_format_for(path: str, default: str) -> str:
    from ...render.output import format_for_path
    fmt = format_for_path(path)
    return fmt.key if fmt is not None else default


__all__ = ["FragRenderWindow", "WINDOW_TITLE"]
