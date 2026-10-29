"""The 3D Editor's *Render…* window: a solid render to an image file, on its own thread.

Same skeleton as the Render Image window (`JobWindowBase`: options left, preview and progress right,
Start / Pause / Stop), reusing its size and output panels. The job (`SolidRenderJob`) makes its own engine
on the worker thread — the GPU one when OpenGL is available, else the CPU one — runs the solid renderer's
passes on a snapshot of the scene, and saves the last image through `render.output.save_image`, so every
format the Render Image window writes is available here too. Quality is the samples per pixel of the
G-buffer (more = fewer holes in the surface), the supersampling and the ambient-occlusion samples.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from typing import Callable

import numpy as np
from PySide6.QtCore import QObject, QSettings, QStandardPaths, QThread, Signal
from PySide6.QtWidgets import QCheckBox, QFormLayout, QGroupBox, QLabel, QMessageBox, QSpinBox, QWidget

from ...fractal.scene import Flame
from ...render.control import RenderControl
from ...render.cpu_engine import CpuEngine
from ...render.final_engine import PHASE_CANCELLED, PHASE_DONE, PHASE_RENDER, PHASE_SAVE, FinalProgress
from ...render.final_settings import FinalRenderSettings
from ...render.gpu_engine import gpu_available
from ...render.output import SaveOptions, output_format, parameters_text, save_image, size_problem, write_sidecar
from ...render.settings import RenderSettings
from ...render.units import format_seconds
from ...scene3d.format import EXTENSION, save_scene
from ...scene3d.model import Scene3D
from ...widgets.icons import render_icon
from ..job_window import JobWindowBase
from ..render_output_panel import OutputPanel
from ..render_progress import RenderProgressPanel
from ..render_size_panel import SizePanel
from .document import Scene3DDocument

WINDOW_TITLE = "Render 3D Image"
SETTINGS_KEY = "three_d/render_settings"
FOLDER_KEY = "final_render/folder"        # shared with the Render Image window: one "last folder"
PROGRESS_INTERVAL = 0.25
POINTS = 1 << 17
FUSE = 20


@dataclass
class SolidRenderOptions:
    """The render quality knobs of this window (the size and output come from the shared panels)."""
    quality: float = 64.0          # samples per output pixel
    passes: int = 8
    oversample: int = 2
    ao_samples: int = 32

    def to_dict(self) -> dict:
        return {"quality": self.quality, "passes": self.passes, "oversample": self.oversample, "ao_samples": self.ao_samples}

    @classmethod
    def from_dict(cls, data: dict) -> "SolidRenderOptions":
        out = cls()
        for key in out.to_dict():
            if key in data:
                setattr(out, key, type(getattr(out, key))(data[key]))
        return out


@dataclass
class SolidOutcome:
    """What a finished solid render reports.

    Attributes:
        image: The render, RGBA8.
        path: Where it was written (None when stopped without `save_incomplete`).
        complete: False if stopped early.
        seconds: Render time (pauses excluded).
        samples: Iterations plotted.
        engine: The engine's name.
        extras: Files written beside the image (parameters, scene).
        notes: Remarks.
    """
    image: np.ndarray
    path: Path | None
    complete: bool
    seconds: float
    samples: int
    engine: str
    extras: list[Path] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


class SolidRenderJob(QThread):
    """One solid render to a file on a worker thread.

    Signals:
        progressed(object): `FinalProgress` (a few per second, with the latest image as the preview).
        succeeded(object): `SolidOutcome`.
        failed(str): The engine could not be set up or the file not written.
    """
    progressed = Signal(object)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, flame: Flame, scene: Scene3D, settings: RenderSettings, output: FinalRenderSettings,
                 parent: QObject | None = None, prefer_gpu: bool = True):
        """Args:
            flame: What to render (copied).
            scene: The materials, lights and environment (copied).
            settings: Size, passes, quality, supersampling.
            output: Destination, format and encoding (only its output fields are used).
            parent: Qt owner.
            prefer_gpu: Try the OpenGL engine first.
        """
        super().__init__(parent)
        self.flame = flame.copy()
        self.scene = scene.copy()
        self.settings = settings.with_solid(self.scene)
        self.output = output
        self.prefer_gpu = prefer_gpu
        self.control = RenderControl()
        self._last_signal = 0.0

    def pause(self) -> None:
        self.control.pause()

    def resume(self) -> None:
        self.control.resume()

    def cancel(self) -> None:
        self.control.cancel()

    @property
    def paused(self) -> bool:
        return self.control.paused

    def run(self) -> None:  # noqa: D401 - QThread entry point
        started = time.perf_counter()
        engine = None
        try:
            engine = self._engine()
            job = engine.start(self.flame, self.settings)
        except Exception as exc:  # noqa: BLE001 - reported, never raised on a thread
            self.failed.emit(str(exc) or exc.__class__.__name__)
            if engine is not None:
                engine.close()
            return
        image = None
        kind = "gpu" if job.stats.engine.startswith("GPU") else "cpu"
        try:
            while not job.stats.finished:
                if not self.control.wait_if_paused():
                    break
                result = job.run_pass(self.control.cancelled)
                if result is None:
                    break
                image = result
                elapsed = time.perf_counter() - started - self.control.paused_seconds
                fraction = job.stats.passes_done / max(1, job.stats.passes_total)
                remaining = elapsed / fraction - elapsed if fraction > 0 else None
                self._report(FinalProgress(PHASE_RENDER, fraction, 0, 0, job.stats.samples, self.settings.samples_total, elapsed, remaining,
                                           job.stats.samples / max(elapsed, 1e-6), job.stats.engine, kind, result), force=False)
            complete = job.stats.finished
            seconds = time.perf_counter() - started - self.control.paused_seconds
            outcome = SolidOutcome(image if image is not None else np.zeros((self.settings.height, self.settings.width, 4), np.uint8),
                                   None, complete, seconds, job.stats.samples, job.stats.engine, notes=list(job.stats.notes))
        finally:
            job.close()
            engine.close()
        if image is not None and self.output.output_path and (complete or self.output.save_incomplete):
            self._report(FinalProgress(PHASE_SAVE, 1.0, 0, 0, outcome.samples, outcome.samples, outcome.seconds, 0.0, 0.0, outcome.engine, kind))
            try:
                self._save(outcome)
            except Exception as exc:  # noqa: BLE001
                self.failed.emit(f"The render finished but could not be saved: {exc}")
                return
        self._report(FinalProgress(PHASE_DONE if complete else PHASE_CANCELLED, 1.0, 0, 0, outcome.samples, outcome.samples, outcome.seconds,
                                   0.0, 0.0, outcome.engine, kind))
        self.succeeded.emit(outcome)

    def _engine(self):
        if self.prefer_gpu and gpu_available()[0]:
            try:
                from ...render.gpu_engine import GpuEngine
                return GpuEngine()
            except Exception:  # noqa: BLE001 - fall back to the CPU
                pass
        return CpuEngine()

    def _report(self, progress: FinalProgress, force: bool = True) -> None:
        now = time.perf_counter()
        if not force and now - self._last_signal < PROGRESS_INTERVAL and progress.fraction < 1.0:
            return
        self._last_signal = now
        self.progressed.emit(progress)

    def _save(self, outcome: SolidOutcome) -> None:
        o = self.output
        path = Path(o.output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        image16 = outcome.image.astype(np.uint16) * 257
        if not o.transparent:
            image16[..., 3] = 65535
        options = SaveOptions(depth=o.depth, transparent=o.transparent, quality=o.lossy_quality, lossless=o.lossless,
                              parameters=parameters_text(self.flame) if o.embed_parameters else "")
        save_image(image16, path, output_format(o.output_format), options)
        outcome.path = path
        if o.save_parameters:
            try:
                outcome.extras.append(write_sidecar(self.flame, path))
                scene_path = path.with_suffix(EXTENSION)
                save_scene(self.scene, scene_path)
                outcome.extras.append(scene_path)
            except OSError as exc:
                outcome.notes.append(f"Parameters could not be written: {exc}")


class SolidQualityPanel(QGroupBox):
    """Samples per pixel, passes, supersampling and AO samples.

    Signals:
        changed(): Any edit.
    """
    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Quality", parent)
        self.quality = QSpinBox(self)
        self.quality.setRange(4, 4000)
        self.quality.setToolTip("Samples per output pixel: more fills the surface more completely (the solid renderer "
                                "keeps the nearest sample per pixel, so holes close as samples accumulate)")
        self.passes = QSpinBox(self)
        self.passes.setRange(1, 64)
        self.passes.setToolTip("Progressive passes: the preview updates after each")
        self.oversample = QSpinBox(self)
        self.oversample.setRange(1, 4)
        self.oversample.setToolTip("Supersampling: the surface is shaded at this many times the output size on each side, then averaged")
        self.ao_samples = QSpinBox(self)
        self.ao_samples.setRange(4, 64)
        self.ao_samples.setToolTip("Ambient-occlusion samples per pixel")
        self.transparent_hint = QCheckBox("Keep the viewport's display mode (points / solid)", self)
        self.transparent_hint.setChecked(True)
        self.transparent_hint.setToolTip("Off: always render the lit solid, whatever the viewport shows")
        form = QFormLayout(self)
        form.addRow("Samples per pixel", self.quality)
        form.addRow("Passes", self.passes)
        form.addRow("Supersample", self.oversample)
        form.addRow("AO samples", self.ao_samples)
        form.addRow(self.transparent_hint)
        for box in (self.quality, self.passes, self.oversample, self.ao_samples):
            box.setKeyboardTracking(False)
            box.valueChanged.connect(lambda _v: self.changed.emit())
        self.transparent_hint.toggled.connect(lambda _on: self.changed.emit())

    def apply(self, options: SolidRenderOptions) -> None:
        self.quality.setValue(int(options.quality))
        self.passes.setValue(options.passes)
        self.oversample.setValue(options.oversample)
        self.ao_samples.setValue(options.ao_samples)

    def read(self) -> SolidRenderOptions:
        return SolidRenderOptions(float(self.quality.value()), self.passes.value(), self.oversample.value(), self.ao_samples.value())


class SolidProgressPanel(RenderProgressPanel):
    """The Render Image window's progress panel, describing a `SolidOutcome` (no tiles here)."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.tiles_caption.hide()
        self.tiles.hide()

    def show_outcome(self, outcome: SolidOutcome) -> None:  # type: ignore[override]
        facts = [f"{'Finished' if outcome.complete else 'Stopped early'} after {format_seconds(outcome.seconds)}",
                 f"{outcome.samples / 1e6:.1f} M samples", outcome.engine]
        line = "  ·  ".join(facts)
        if outcome.path is not None:
            p = outcome.path
            line += f"<br>Saved {self.file_link(p)} in {self.file_link(p.parent, str(p.parent))}"
            if outcome.extras:
                line += " (+ " + ", ".join(self.file_link(x) for x in outcome.extras) + ")"
        elif not outcome.complete:
            line += "<br>Nothing was saved (stopped before completion; see 'Save incomplete renders')."
        notes = [n for n in outcome.notes if n]
        if notes:
            line += "<br><i>" + "; ".join(notes) + "</i>"
        self.result.setText(line)


class SolidRenderWindow(JobWindowBase):
    """Render the 3D Editor's scene to an image file (see the module docstring)."""
    title = WINDOW_TITLE
    quit_question = "A 3D render is still running. Stop it and quit?"

    def __init__(self, document: Scene3DDocument, parent: QWidget | None = None, settings: QSettings | None = None,
                 prefer_gpu: bool = True, preview_size: Callable[[], tuple[int, int]] | None = None):
        """Args:
            document: The scene to render (copied when Start is pressed).
            parent: Owning window; when given this becomes a child top-level window.
            settings: Where options persist.
            prefer_gpu: Try the OpenGL engine first.
            preview_size: Returns the viewport's size, the size panel's "preview size" preset (None: the flame's own size).
        """
        super().__init__(parent, settings)
        self.setWindowIcon(render_icon())
        self.document = document
        self.prefer_gpu = prefer_gpu
        self._preview_size = preview_size
        self.job: SolidRenderJob | None = None
        self.last_outcome: SolidOutcome | None = None
        self.size_panel = SizePanel(self)
        self.quality_panel = SolidQualityPanel(self)
        self.output_panel = OutputPanel(self)
        for widget in (self.output_panel.save_details, self.output_panel.details_format):
            widget.hide()                                  # no details report for solid renders
        self.output_panel.save_parameters.setText(f"Save parameters (.flame and {EXTENSION}) beside the image")
        self.plan_label = QLabel(self)
        self.plan_label.setWordWrap(True)
        self.progress_panel = SolidProgressPanel(self)
        self._build_layout(self.progress_panel, (1100, 680))
        self._load()
        self.size_panel.size_changed.connect(self._on_options_changed)
        self.quality_panel.changed.connect(self._on_options_changed)
        self.output_panel.changed.connect(self._on_options_changed)
        for signal in (document.scene_replaced, document.scene_restored, document.fractal_changed):
            signal.connect(self._on_scene_changed)
        self._on_scene_changed()

    def _option_widgets(self) -> list[QWidget]:
        return [self.size_panel, self.quality_panel, self.output_panel, self.plan_label]

    def _option_panels(self) -> list[QWidget]:
        return [self.size_panel, self.quality_panel, self.output_panel]

    # --- settings -----------------------------------------------------------------------------------------------
    def _load(self) -> None:
        stored = self._settings.value(SETTINGS_KEY, "")
        options, output = SolidRenderOptions(), FinalRenderSettings()
        if stored:
            try:
                data = json.loads(stored)
                options = SolidRenderOptions.from_dict(data.get("quality", {}))
                output = FinalRenderSettings.from_dict(data.get("output", {}))
            except (TypeError, ValueError, AttributeError):
                pass
        self.size_panel.set_size(output.width, output.height)
        self.quality_panel.apply(options)
        self.output_panel.apply(output)

    def _persist(self) -> None:
        output = self.output_settings()
        self._settings.setValue(SETTINGS_KEY, json.dumps({"quality": self.quality_panel.read().to_dict(), "output": output.to_dict()}))
        if output.output_path:
            self._settings.setValue(FOLDER_KEY, str(Path(output.output_path).parent))

    def output_settings(self) -> FinalRenderSettings:
        """The size and output fields as the shared panels describe them."""
        return self.output_panel.read(FinalRenderSettings().with_size(*self.size_panel.size()))

    def render_settings(self) -> RenderSettings:
        """The engine settings for the chosen size and quality."""
        options = self.quality_panel.read()
        width, height = self.size_panel.size()
        return RenderSettings(width, height, passes=options.passes, quality=options.quality, points=POINTS, fuse=FUSE,
                              oversample=options.oversample, filter_radius=0.0, refine_to=0.0)

    def _scene_for_render(self) -> Scene3D:
        scene = self.document.scene.copy()
        options = self.quality_panel.read()
        scene.solid.ao_samples = options.ao_samples
        if not self.quality_panel.transparent_hint.isChecked():
            scene.solid.display = "solid"
        if self.output_panel.transparent.isChecked():
            scene.environment.visible = False
        return scene

    # --- document -----------------------------------------------------------------------------------------------
    def _on_scene_changed(self) -> None:
        flame = self.document.flame
        self.setWindowTitle(f"{WINDOW_TITLE} — {flame.name}" if flame else WINDOW_TITLE)
        if flame is not None:
            width, height = self._preview_size() if self._preview_size is not None else (flame.camera.width, flame.camera.height)
            self.size_panel.set_preview_size(max(1, width), max(1, height))
            self.output_panel.set_path(self._default_path(flame.name))
        self._on_options_changed()

    def _default_path(self, name: str) -> str:
        current = self.output_panel.path.text().strip()
        folder = Path(current).parent if current else Path(self._settings.value(
            FOLDER_KEY, QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation) or str(Path.home())))
        fmt = output_format(self.output_panel.format_box.currentData())
        stem = re.sub(r'[\\/:*?"<>|]+', "_", name).strip() or "fractal"
        return str(folder / f"{stem}-3d{fmt.extension}")

    def _problems(self) -> list[str]:
        output = self.output_settings()
        problems = []
        if not output.output_path.strip():
            problems.append("Choose where to save the image")
        issue = size_problem(output_format(output.output_format), output.width, output.height)
        if issue:
            problems.append(issue)
        if self.document.flame is None:
            problems.append("No fractal is loaded in the 3D Editor")
        return problems

    def _on_options_changed(self, *_args) -> None:
        self._persist()
        problems = self._problems()
        self.start_button.setEnabled(not problems and self.job is None)
        self.start_button.setToolTip("\n".join(problems))
        if problems and self.job is None:
            self.plan_label.setText('<span style="color:#c0392b">' + "; ".join(problems) + "</span>")
            return
        s = self.render_settings()
        gpu = self.prefer_gpu and gpu_available()[0]
        self.plan_label.setText(f"{s.width} × {s.height}, {s.quality:g} samples per pixel in {s.passes} passes, "
                                f"{s.oversample}× supersampling — {'GPU' if gpu else 'CPU'} solid renderer")
        if self.job is None and not self._showing_result:
            self.progress_panel.show_idle("")

    # --- rendering ------------------------------------------------------------------------------------------------
    def start(self, ask_overwrite: bool = True) -> None:
        flame = self.document.flame
        if flame is None or self.job is not None:
            return
        problems = self._problems()
        if problems:
            QMessageBox.warning(self, WINDOW_TITLE, "\n".join(problems))
            return
        output = self.output_settings()
        if ask_overwrite and Path(output.output_path).exists():
            answer = QMessageBox.question(self, WINDOW_TITLE, f"{Path(output.output_path).name} already exists. Overwrite it?",
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
        self._persist()
        flame = flame.copy()
        flame.camera = flame.camera.at_size(output.width, output.height)
        job = SolidRenderJob(flame, self._scene_for_render(), self.render_settings(), output, self, self.prefer_gpu)
        self._launch(job, FinalProgress(phase="Starting the engine", tiles=0, engine=""))

    def _on_progress(self, progress: FinalProgress) -> None:
        self.progress_panel.show_progress(progress)

    def _on_succeeded(self, outcome: SolidOutcome) -> None:
        self.last_outcome = outcome
        self._showing_result = True
        self.progress_panel.show_outcome(outcome)


__all__ = ["SolidRenderWindow", "SolidRenderJob", "SolidRenderOptions", "SolidOutcome", "SolidQualityPanel"]
