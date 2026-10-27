"""Runs a final render on its own thread and reports to the GUI through signals.

    job = FinalRenderJob(flame, settings, parent)
    job.progressed.connect(...)       # FinalProgress, throttled to a few per second
    job.succeeded.connect(...)        # FinalOutcome
    job.failed.connect(...)           # str
    job.start()                       # pause() / resume() / cancel() while it runs

One job per render: the thread creates its own OpenGL context (contexts are thread-bound) or
CPU worker processes, renders, saves, and exits. The main window's preview engine keeps working
meanwhile, so the user can carry on editing another fractal. The flame is copied at start, so
later edits never leak into a running render.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

from ..fractal.scene import Flame
from .final_engine import PHASE_SAVE, FinalProgress, FinalRenderer, FinalResult
from .final_settings import FinalRenderSettings
from .output import SaveOptions, output_format, parameters_text, save_image, write_sidecar
from .samplers import RenderControl

PROGRESS_INTERVAL = 0.25   # seconds between progress signals (previews always go through)


@dataclass
class FinalOutcome:
    """What a finished job reports.

    Attributes:
        result: The render.
        path: Where the image was written (None if not saved — cancelled without `save_incomplete`, or no path).
        sidecar: The `.flame` written beside it, if any.
        notes: Engine remarks plus anything that went wrong while saving extras.
    """
    result: FinalResult
    path: Path | None
    sidecar: Path | None = None
    notes: list[str] = field(default_factory=list)


class FinalRenderJob(QThread):
    """One final render, start to saved file, on a worker thread.

    Signals:
        progressed(object): FinalProgress (at most a few per second, plus every preview).
        succeeded(object): FinalOutcome when the render finished or was stopped with a saved result.
        failed(str): The render could not be set up or saving failed.
    """
    progressed = Signal(object)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, flame: Flame, settings: FinalRenderSettings, parent: QObject | None = None):
        super().__init__(parent)
        self.flame = flame.copy()
        self.settings = settings
        self.control = RenderControl()
        self.started_at = 0.0
        self._last_signal = 0.0
        self._last_progress: FinalProgress | None = None

    # --- control (GUI thread) ----------------------------------------------------------------
    def pause(self) -> None:
        """Hold the render between chunks."""
        self.control.pause()

    def resume(self) -> None:
        """Continue a paused render."""
        self.control.resume()

    def cancel(self) -> None:
        """Stop the render (what was rendered is saved if `save_incomplete` is set)."""
        self.control.cancel()

    @property
    def paused(self) -> bool:
        """True while paused."""
        return self.control.paused

    # --- worker thread ------------------------------------------------------------------------
    def run(self) -> None:  # noqa: D401 - QThread entry point
        self.started_at = time.perf_counter()
        try:
            result = FinalRenderer(self.flame, self.settings, self.control).run(self._report)
        except Exception as exc:  # noqa: BLE001 - anything from the engine is reported, never raised on a thread
            self.failed.emit(str(exc) or exc.__class__.__name__)
            return
        outcome = FinalOutcome(result, None, notes=list(result.notes))
        final = self._last_progress
        if self.settings.output_path and (result.complete or self.settings.save_incomplete):
            self.progressed.emit(replace(final, phase=PHASE_SAVE, preview=None))
            try:
                outcome.path = self._save(result)
            except Exception as exc:  # noqa: BLE001 - report, keep the result
                self.failed.emit(f"The render finished but could not be saved: {exc}")
                return
            if self.settings.save_parameters:
                try:
                    outcome.sidecar = write_sidecar(self.flame, outcome.path)
                except OSError as exc:
                    outcome.notes.append(f"Parameters could not be written: {exc}")
            self.progressed.emit(replace(final, preview=None))   # back to Finished / Stopped once the file is written
        self.succeeded.emit(outcome)

    def _report(self, progress: FinalProgress) -> None:
        self._last_progress = progress
        now = time.perf_counter()
        if progress.preview is None and now - self._last_signal < PROGRESS_INTERVAL and progress.fraction < 1.0:
            return
        self._last_signal = now
        self.progressed.emit(progress)

    def _save(self, result: FinalResult) -> Path:
        s = self.settings
        path = Path(s.output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        options = SaveOptions(depth=s.depth, transparent=s.transparent, quality=s.lossy_quality, lossless=s.lossless,
                              parameters=parameters_text(self.flame) if s.embed_parameters else "")
        save_image(result.image, path, output_format(s.output_format), options)
        return path


__all__ = ["FinalRenderJob", "FinalOutcome"]
