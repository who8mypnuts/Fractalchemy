"""The Render Animation window: the Render Image window's size / quality panels, a folder instead of a file, frames, ffmpeg.

Opened from the Animation window's *Render Animation…*. A non-modal tool window: the batch runs on
its own thread (`AnimationRenderJob`) with a snapshot of the animation, so the Animation and main
windows stay usable. Settings persist in QSettings and travel with the `.faanim` file (the last
render settings are saved in it, so a render can be repeated later). The panels are in
`animation_render_panels.py`; the job plumbing is `JobWindowBase`'s.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths
from PySide6.QtWidgets import QLabel, QMessageBox, QWidget

from ..animation.render import AnimationRenderSettings, safe_stem
from ..animation.render_job import PHASE_ENCODE, AnimationOutcome, AnimationProgress, AnimationRenderJob
from ..render.estimate import RateHint, RenderEstimate, engine_kind
from ..render.final_engine import PHASE_CANCELLED, PHASE_DONE
from ..render.final_settings import FinalRenderSettings, plan_tiles
from ..render.gpu_engine import gpu_available
from ..render.units import format_rate, format_seconds
from ..widgets.icons import editor_icon
from .animation_document import AnimationDocument
from .animation_render_panels import AnimationOutputPanel, AnimationProgressPanel, VideoPanel
from .job_window import JobWindowBase
from .render_quality_panel import QualityPanel
from .render_size_panel import SizePanel

WINDOW_TITLE = "Render Animation"
SETTINGS_KEY = "animation_render/settings"
FOLDER_KEY = "animation_render/folder"


class AnimationRenderWindow(JobWindowBase):
    """Non-modal batch render dialog bound to an AnimationDocument (see the module docstring)."""
    title = WINDOW_TITLE
    quit_question = "An animation render is still running. Stop it and quit?"

    def __init__(self, document: AnimationDocument, parent: QWidget | None = None, settings: QSettings | None = None,
                 rate_hint: RateHint | None = None):
        """Args:
            document: The animation to render (copied when Start is pressed).
            parent: Owning window; when given this becomes a child top-level window.
            settings: Where options persist (the application's store by default).
            rate_hint: Returns (engine name, samples per second) of the preview engine, for the time estimate.
        """
        super().__init__(parent, settings)
        self.setWindowIcon(editor_icon("anim-render"))
        self.document = document
        self._rate_hint = rate_hint
        self._estimate = RenderEstimate()
        self.job: AnimationRenderJob | None = None
        self.last_outcome: AnimationOutcome | None = None
        self.size_panel = SizePanel(self)
        self.size_panel.preview_label = "Keyframe size"
        self.size_panel.presets.setToolTip("Common screen and print sizes; 'Keyframe size' is the first keyframe's own image size")
        self.quality_panel = QualityPanel(self)
        self.output_panel = AnimationOutputPanel(self)
        self.video_panel = VideoPanel(self)
        self.plan_label = QLabel(self)
        self.estimate_label = QLabel(self)
        self.progress_panel = AnimationProgressPanel(self)
        for label in (self.plan_label, self.estimate_label):
            label.setWordWrap(True)
        self._build_layout(self.progress_panel, (1160, 780))
        self._load()
        self._connect()
        self._on_animation_replaced()

    # --- construction -----------------------------------------------------------------------------------------
    def _option_widgets(self) -> list[QWidget]:
        return [self.size_panel, self.quality_panel, self.output_panel, self.video_panel, self.plan_label, self.estimate_label]

    def _option_panels(self) -> list[QWidget]:
        return [self.size_panel, self.quality_panel, self.output_panel, self.video_panel]

    def _connect(self) -> None:
        self.size_panel.size_changed.connect(self._on_options_changed)
        for panel in (self.quality_panel, self.output_panel, self.video_panel):
            panel.changed.connect(self._on_options_changed)
        self.document.animation_replaced.connect(self._on_animation_replaced)
        self.document.settings_changed.connect(self._on_animation_changed)
        self.document.keyframes_changed.connect(self._on_animation_changed)

    def _load(self) -> None:
        settings = AnimationRenderSettings()
        stored = self._settings.value(SETTINGS_KEY, "")
        if stored:
            try:
                settings = AnimationRenderSettings.from_dict(json.loads(stored))
            except (TypeError, ValueError):
                pass
        self._apply(settings)

    def _apply(self, settings: AnimationRenderSettings) -> None:
        """Show `settings` in every panel (no signals)."""
        self.size_panel.set_size(settings.image.width, settings.image.height)
        self.quality_panel.apply(settings.image)
        self.output_panel.apply(settings, self.document.animation.total_frames)
        self.video_panel.apply(settings)

    # --- settings ---------------------------------------------------------------------------------------------
    def current_settings(self) -> AnimationRenderSettings:
        """What the panels currently describe."""
        image = self.quality_panel.read(FinalRenderSettings().with_size(*self.size_panel.size()))
        settings = self.output_panel.read(AnimationRenderSettings(image=image))
        return self.video_panel.read(settings)

    def _persist(self) -> None:
        """Keep the settings in QSettings and with the animation (the `.faanim` file carries them)."""
        s = self.current_settings()
        self._settings.setValue(SETTINGS_KEY, json.dumps(s.to_dict()))
        if s.folder:
            self._settings.setValue(FOLDER_KEY, s.folder)
        self.document.set_render_settings(s.to_dict())

    # --- document ---------------------------------------------------------------------------------------------
    def _on_animation_replaced(self) -> None:
        anim = self.document.animation
        self.setWindowTitle(f"{WINDOW_TITLE} — {self.document.title}")
        if anim.render:
            try:
                self._apply(AnimationRenderSettings.from_dict(anim.render))
            except (TypeError, ValueError):
                pass
        self._on_animation_changed()
        if not self.output_panel.folder.text().strip():
            self.output_panel.folder.setText(self._default_folder())
        if self.output_panel.base_name.text().strip() in ("", "frame"):
            self.output_panel.set_base_name(safe_stem(anim.name) or "frame")
        self._on_options_changed()

    def _on_animation_changed(self) -> None:
        """The length or the keyframes changed: bound the frame range, follow the first keyframe's size."""
        anim = self.document.animation
        if anim.keyframes:
            cam = anim.keyframes[0].flame.camera
            self.size_panel.set_preview_size(cam.width, cam.height)
        self.output_panel.set_total_frames(anim.total_frames)
        self._on_options_changed()

    def _default_folder(self) -> str:
        stored = self._settings.value(FOLDER_KEY)
        base = Path(stored) if stored else Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation) or Path.home())
        return str(base / (safe_stem(self.document.animation.name) or "animation"))

    # --- plan / estimate ----------------------------------------------------------------------------------------
    def _problems(self, s: AnimationRenderSettings) -> list[str]:
        problems = s.problems(self.document.animation.total_frames)
        if not self.document.animation.keyframes:
            problems.append("The animation has no keyframes")
        return problems

    def _on_options_changed(self, *_args) -> None:
        s = self.current_settings()
        anim = self.document.animation
        self._persist()
        problems = self._problems(s)
        self.start_button.setEnabled(not problems and self.job is None)
        self.start_button.setToolTip("\n".join(problems))
        frames = s.frames(anim.total_frames)
        self.video_panel.show_command(s, anim.fps, anim.total_frames, frames[0] if frames else 0)
        if problems and self.job is None:
            self.plan_label.setText('<span style="color:#c0392b">' + "; ".join(problems) + "</span>")
            self.estimate_label.setText("")
            return
        kind = engine_kind(s.image, gpu_available()[0])
        plan = plan_tiles(s.image, gpu=kind == "gpu")
        total = s.image.samples_per_tile * plan.count * len(frames)
        self.plan_label.setText(self._plan_text(s, frames, plan.count))
        rate = self._estimate.rate_for(kind, self._rate_hint() if self._rate_hint is not None else None)
        if rate is None:
            self.estimate_label.setText(f"{total / 1e9:.2f} G samples to run. Time unknown until an engine has measured its speed.")
        else:
            self.estimate_label.setText(f"{total / 1e9:.2f} G samples to run — roughly {format_seconds(total / rate[1])} at {rate[0]} "
                                        f"({format_rate(rate[1])}), plus filtering and saving.")
        if self.job is None and not self._showing_result:
            self.progress_panel.show_idle(f"≈ {format_seconds(total / rate[1])}" if rate else "")

    def _plan_text(self, s: AnimationRenderSettings, frames: list[int], tiles: int) -> str:
        total = self.document.animation.total_frames
        text = f"{len(frames)} frame{'s' if len(frames) != 1 else ''} of {s.image.width} × {s.image.height}"
        if tiles > 1:
            text += f" in {tiles} tiles each"
        text += f" → {s.frame_path(frames[0], total).name}"
        if len(frames) > 1:
            text += f" … {s.frame_path(frames[-1], total).name}"
        if s.video:
            text += f", then {s.video_path().name}"
        return text

    # --- rendering ---------------------------------------------------------------------------------------------
    def start(self, ask_overwrite: bool = True) -> None:
        """Snapshot the animation and settings and start the batch thread.

        Args:
            ask_overwrite: Confirm before replacing existing frame files (tests pass False).
        """
        if self.job is not None:
            return
        anim = self.document.animation
        s = self.current_settings()
        problems = self._problems(s)
        if problems:
            QMessageBox.warning(self, WINDOW_TITLE, "\n".join(problems))
            return
        frames = s.frames(anim.total_frames)
        existing = [f for f in frames if s.frame_path(f, anim.total_frames).exists()]
        if ask_overwrite and existing and not s.skip_existing:
            answer = QMessageBox.question(self, WINDOW_TITLE, f"{len(existing)} of the {len(frames)} frame files already exist in "
                                          f"{s.folder}. Overwrite them?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
        self._persist()
        self._launch(AnimationRenderJob(anim, s, self), AnimationProgress(phase="Starting the engine", count=len(frames)))

    def _on_progress(self, progress: AnimationProgress) -> None:
        fp = progress.frame_progress
        if fp is not None and fp.phase in (PHASE_DONE, PHASE_CANCELLED):
            self._estimate.record(fp.engine_kind, fp.rate)
        self.progress_panel.show_progress(progress)
        if progress.phase == PHASE_ENCODE:
            self.pause_button.setEnabled(False)     # ffmpeg cannot be paused

    def _on_succeeded(self, outcome: AnimationOutcome) -> None:
        self.last_outcome = outcome
        self._showing_result = True
        self.progress_panel.show_outcome(outcome, Path(self.current_settings().folder))


__all__ = ["AnimationRenderWindow", "WINDOW_TITLE"]
