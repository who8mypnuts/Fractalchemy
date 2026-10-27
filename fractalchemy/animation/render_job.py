"""Renders every frame of an animation on a worker thread, then (optionally) encodes the video with ffmpeg.

    job = AnimationRenderJob(animation, settings, parent)
    job.progressed.connect(...)       # AnimationProgress
    job.succeeded.connect(...)        # AnimationOutcome
    job.failed.connect(...)           # str
    job.start()                       # pause() / resume() / cancel() while it runs

One sampler (GPU context or CPU worker processes) is created for the whole batch and re-aimed at
each frame's flame (`Sampler.set_flame`), so the per-frame cost is the render itself, not engine
start-up. Each frame goes through the same `FinalRenderer` as a single image and is saved with the
same writers, under `base_0001.png`-style names. The animation is copied at start, so edits in the
Animation window never leak into a running render.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
from PySide6.QtCore import QObject, QThread, Signal

from ..render.compiled import CompiledFlame
from ..render.control import RenderControl
from ..render.final_engine import PHASE_CANCELLED, PHASE_DONE, FinalProgress, FinalRenderer, FinalResult
from ..render.output import SaveOptions, output_format, parameters_text, save_image, write_sidecar
from ..render.samplers import Sampler, create_sampler
from .model import Animation
from .render import AnimationRenderSettings, ffmpeg_command

PROGRESS_INTERVAL = 0.25
PHASE_ENCODE = "Encoding the video"
PHASE_FRAME = "Rendering"


@dataclass
class AnimationProgress:
    """A progress report for the Render Animation window.

    Attributes:
        phase: `Rendering`, `Encoding the video`, `Finished` or `Stopped`.
        frame: The frame being rendered (its number in the animation).
        index, count: Position in the batch (1-based) and the batch size.
        fraction: Overall progress 0..1 (frames done plus the current frame's progress).
        elapsed: Seconds since the start, pauses excluded.
        remaining: Estimated seconds to go (from the frames finished so far), or None before the first frame.
        frame_progress: The current frame's own report (tile, rate, preview…), if any.
        preview: RGBA8 picture of the latest frame state, or None if unchanged.
        engine: Sampler name.
    """
    phase: str = PHASE_FRAME
    frame: int = 0
    index: int = 0
    count: int = 0
    fraction: float = 0.0
    elapsed: float = 0.0
    remaining: float | None = None
    frame_progress: FinalProgress | None = None
    preview: np.ndarray | None = None
    engine: str = ""


@dataclass
class AnimationOutcome:
    """What a finished batch reports.

    Attributes:
        frames: Paths of the frames written (in order).
        skipped: Frames left alone because their file existed.
        video: The video written, if any.
        complete: False if the batch was stopped early.
        seconds: Time taken, pauses excluded.
        samples: Iterations over all frames.
        engine: Sampler name.
        notes: Remarks (engine fallback, ffmpeg output…).
    """
    frames: list[Path] = field(default_factory=list)
    skipped: list[int] = field(default_factory=list)
    video: Path | None = None
    complete: bool = True
    seconds: float = 0.0
    samples: int = 0
    engine: str = ""
    notes: list[str] = field(default_factory=list)


class AnimationRenderJob(QThread):
    """The batch, start to the last file, on a worker thread (see the module docstring).

    Signals:
        progressed(object): AnimationProgress.
        succeeded(object): AnimationOutcome when the batch finished or was stopped.
        failed(str): Nothing could be rendered (engine failure, unwritable folder…).
    """
    progressed = Signal(object)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, animation: Animation, settings: AnimationRenderSettings, parent: QObject | None = None):
        super().__init__(parent)
        self.animation = animation.copy()
        self.settings = settings
        self.control = RenderControl()
        self.frames = settings.frames(self.animation.total_frames)
        self._last_signal = 0.0
        self._started = 0.0
        self._frame_seconds: list[float] = []
        self._process: subprocess.Popen | None = None
        self._progress = AnimationProgress(count=len(self.frames))

    # --- control (GUI thread) --------------------------------------------------------------------------------
    def pause(self) -> None:
        self.control.pause()

    def resume(self) -> None:
        self.control.resume()

    def cancel(self) -> None:
        self.control.cancel()
        process = self._process
        if process is not None and process.poll() is None:
            process.terminate()

    @property
    def paused(self) -> bool:
        return self.control.paused

    # --- worker thread --------------------------------------------------------------------------------------
    def run(self) -> None:  # noqa: D401 - QThread entry point
        self._started = time.perf_counter()
        outcome = AnimationOutcome()
        try:
            Path(self.settings.folder).mkdir(parents=True, exist_ok=True)
            self._render_frames(outcome)
        except Exception as exc:  # noqa: BLE001 - reported, never raised on a thread
            if not outcome.frames:
                self.failed.emit(str(exc) or exc.__class__.__name__)
                return
            outcome.notes.append(f"Stopped by an error: {exc}")
            outcome.complete = False
        if outcome.complete and self.settings.video and (outcome.frames or outcome.skipped):
            self._encode(outcome)
        outcome.seconds = self._elapsed()
        self._emit(replace(self._progress, phase=PHASE_DONE if outcome.complete else PHASE_CANCELLED, fraction=1.0,
                           remaining=0.0, preview=None), force=True)
        self.succeeded.emit(outcome)

    def _render_frames(self, outcome: AnimationOutcome) -> None:
        sampler: Sampler | None = None
        try:
            for index, frame in enumerate(self.frames):
                if self.control.cancelled():
                    outcome.complete = False
                    return
                path = self.settings.frame_path(frame, self.animation.total_frames)
                if self.settings.skip_existing and path.exists():
                    outcome.skipped.append(frame)
                    self._frame_done(index, frame)
                    continue
                flame = self.animation.flame_at(frame)
                if flame is None:
                    raise ValueError("the animation has no keyframes")
                compiled = CompiledFlame.build(flame)
                if sampler is None:
                    sampler, note = create_sampler(flame, compiled, self.settings.image.engine, self.settings.image.cpu_threads,
                                                   self.settings.image.seed, self.settings.image.fuse)
                    outcome.engine = sampler.name
                    if note:
                        outcome.notes.append(note)
                else:
                    sampler.set_flame(flame, compiled)
                started = time.perf_counter()
                self._progress = replace(self._progress, frame=frame, index=index + 1, engine=sampler.name, phase=PHASE_FRAME)
                result = FinalRenderer(flame, self.settings.image, self.control, sampler=sampler).run(
                    lambda p, i=index: self._report_frame(i, p))
                outcome.samples += result.samples
                if not result.complete and not self.settings.image.save_incomplete:
                    outcome.complete = False
                    return
                self._save(flame, result, path, outcome)
                outcome.frames.append(path)
                self._frame_seconds.append(time.perf_counter() - started)
                self._frame_done(index, frame, result)
                if not result.complete:
                    outcome.complete = False
                    return
        finally:
            if sampler is not None:
                sampler.close()

    def _save(self, flame, result: FinalResult, path: Path, outcome: AnimationOutcome) -> None:
        s = self.settings.image
        options = SaveOptions(depth=s.depth, transparent=s.transparent, quality=s.lossy_quality, lossless=s.lossless,
                              parameters=parameters_text(flame) if s.embed_parameters else "")
        save_image(result.image, path, output_format(s.output_format), options)
        if s.save_parameters:
            try:
                write_sidecar(flame, path)
            except OSError as exc:
                outcome.notes.append(f"Parameters of frame {path.name} could not be written: {exc}")

    def _encode(self, outcome: AnimationOutcome) -> None:
        """Run ffmpeg over the frames; its problems become notes, not failures (the frames are on disk)."""
        self._emit(replace(self._progress, phase=PHASE_ENCODE, fraction=1.0, remaining=None, preview=None), force=True)
        command = ffmpeg_command(self.settings, self.animation.fps, self.animation.total_frames, self.frames[0])
        try:
            self._process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                             stdin=subprocess.DEVNULL)
        except OSError as exc:
            outcome.notes.append(f"ffmpeg could not be started: {exc}")
            return
        output, _ = self._process.communicate()
        code = self._process.returncode
        self._process = None
        if self.control.cancelled():
            outcome.complete = False
            outcome.notes.append("The video was not finished (stopped)")
        elif code != 0:
            tail = " ".join((output or "").strip().splitlines()[-3:])
            outcome.notes.append(f"ffmpeg failed (exit code {code}): {tail or 'no output'}")
        else:
            outcome.video = self.settings.video_path()
            if not self.settings.keep_frames:
                for path in outcome.frames:
                    try:
                        path.unlink()
                    except OSError:
                        pass
                outcome.frames = []
                outcome.notes.append("The frame images were removed after encoding")

    # --- progress -------------------------------------------------------------------------------------------
    def _elapsed(self) -> float:
        return time.perf_counter() - self._started - self.control.paused_seconds

    def _remaining(self, frames_left: float) -> float | None:
        if not self._frame_seconds:
            return None
        return max(0.0, frames_left * (sum(self._frame_seconds) / len(self._frame_seconds)))

    def _report_frame(self, index: int, progress: FinalProgress) -> None:
        count = max(1, len(self.frames))
        self._progress = replace(self._progress, frame_progress=progress, fraction=(index + progress.fraction) / count,
                                 elapsed=self._elapsed(), remaining=self._remaining(count - index - progress.fraction),
                                 preview=progress.preview)
        self._emit(self._progress, force=progress.preview is not None)

    def _frame_done(self, index: int, frame: int, result: FinalResult | None = None) -> None:
        count = max(1, len(self.frames))
        preview = None
        if result is not None:
            preview = (result.image >> 8).astype(np.uint8) if result.image.dtype == np.uint16 else result.image
        self._progress = replace(self._progress, frame=frame, index=index + 1, fraction=(index + 1) / count,
                                 elapsed=self._elapsed(), remaining=self._remaining(count - index - 1), preview=preview)
        self._emit(self._progress, force=True)

    def _emit(self, progress: AnimationProgress, force: bool = False) -> None:
        now = time.perf_counter()
        if not force and now - self._last_signal < PROGRESS_INTERVAL:
            return
        self._last_signal = now
        self.progressed.emit(progress)


__all__ = ["AnimationRenderJob", "AnimationProgress", "AnimationOutcome", "PHASE_ENCODE", "PHASE_FRAME"]
