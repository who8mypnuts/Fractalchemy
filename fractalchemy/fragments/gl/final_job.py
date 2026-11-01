"""A hi-res / animation render on its own thread with its own OpenGL context — the fragment twin of `FinalRenderJob`.

The window snapshots everything at *Start* (the request, the parameter state, presets, curves, the plan); the thread
creates a `FragEngine`, runs `FragFinalRenderer`, writes every frame as it is assembled (the image, a `.fragparams`
beside it, the fragment with its settings into a `<name> Files` folder — FragM's autosave — and the includes when
asked), reports `FinalProgress` a few times a second with a preview of the last frame, and ends with a `FragOutcome`.
Pause / Stop go through a `RenderControl`; *save incomplete* keeps what was written before a stop.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

from ...render.control import RenderControl
from ...render.final_engine import PHASE_SAVE, FinalProgress
from ..animation import AnimationSettings, camera_path, keyframe_blend
from ..document_format import PARAMS_SUFFIX, write_fragment, write_parameters
from ..easing import EasingSetting
from ..render_settings import FragFinalSettings, safe_stem
from ..source import FragmentSource
from ..state import ParameterState
from .engine import FragEngine
from .final import FragFinalRenderer, FragFinalResult, FrameImage, to_display_rgba8, write_frame
from .job import FragRequest


@dataclass
class FragOutcome:
    """What a finished job reports (duck-typed for `RenderProgressPanel.show_outcome`).

    Attributes:
        result: The renderer's result.
        path: The (first / only) image written, None when nothing was saved.
        sidecar: The `.fragparams` beside it, if any.
        report: The saved fragment (`<name> Files/<name>.frag`), if any.
        notes: Remarks (files written, problems with extras).
        frames: Every frame image written.
        video: The video ffmpeg produced, if any.
    """
    result: FragFinalResult
    path: Path | None
    sidecar: Path | None = None
    report: Path | None = None
    notes: list[str] = field(default_factory=list)
    frames: list[Path] = field(default_factory=list)
    video: Path | None = None


@dataclass
class FragRenderInput:
    """The snapshot the job renders from.

    Attributes:
        request: The program and base values.
        state: The parameter state (copied by the renderer).
        source: The preprocessed fragment (presets, flags, dependencies).
        text: The fragment's source text (for the saved fragment).
        name: The fragment's name (file stem).
        animation: The clock.
        curves: The easing curves.
        settings: The plan.
        settings_text: The parameters as settings text (embedded in the image, written beside it).
    """
    request: FragRequest
    state: ParameterState
    source: FragmentSource
    text: str
    name: str
    animation: AnimationSettings
    curves: list[EasingSetting]
    settings: FragFinalSettings
    settings_text: str


class FragRenderJob(QThread):
    """One hi-res / animation render, start to saved files, on a worker thread.

    Signals:
        progressed(object): `FinalProgress`.
        succeeded(object): `FragOutcome` when the render finished or was stopped with saved frames.
        failed(str): The render could not be set up or nothing could be written.
    """
    progressed = Signal(object)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, inputs: FragRenderInput, parent: QObject | None = None):
        super().__init__(parent)
        self.inputs = inputs
        self.control = RenderControl()
        self.started_at = 0.0
        self._written: list[Path] = []
        self._last_progress: FinalProgress | None = None
        self._notes: list[str] = []
        self._engine: FragEngine | None = None

    # --- control (GUI thread) ------------------------------------------------------------------------------------------
    def pause(self) -> None:
        self.control.pause()

    def resume(self) -> None:
        self.control.resume()

    def cancel(self) -> None:
        self.control.cancel()

    @property
    def paused(self) -> bool:
        return self.control.paused

    # --- worker thread ----------------------------------------------------------------------------------------------------
    def run(self) -> None:  # noqa: D401 - QThread entry point
        self.started_at = time.perf_counter()
        i = self.inputs
        try:
            self._engine = FragEngine()
            path = camera_path(i.source.presets, i.animation) if i.source.keyframe_names() else None
            renderer = FragFinalRenderer(self._engine, i.request, i.state, i.settings, i.animation, path, i.curves, i.source.auto_focus,
                                         self.control, keyframe_blend(i.source.presets, i.state, i.animation))
            if i.settings.save_fragment and not i.settings.preview:
                self._save_fragment()
            result = renderer.run(self._report, self._frame_done)
        except Exception as exc:  # noqa: BLE001 - anything from the engine is reported, never raised on a thread
            self.failed.emit(str(exc) or exc.__class__.__name__)
            return
        finally:
            if self._engine is not None:
                self._engine.close()
                self._engine = None
        outcome = FragOutcome(result, self._written[0] if self._written else None, frames=list(self._written))
        if i.settings.animation and i.settings.video and result.complete and self._written:
            self._encode(outcome)
        result.paths = list(self._written)
        result.notes = list(self._notes)
        outcome.notes = list(self._notes)
        if i.settings.save_parameters and self._written:
            outcome.sidecar = self._written[0].with_suffix(PARAMS_SUFFIX)
        if i.settings.save_fragment and not i.settings.preview:
            outcome.report = self._fragment_path()
        self.succeeded.emit(outcome)

    def _report(self, progress: FinalProgress) -> None:
        self._last_progress = progress
        self.progressed.emit(progress)

    def _frame_done(self, image: FrameImage) -> None:
        """Write one assembled frame (unless previewing) and show it."""
        i = self.inputs
        preview = to_display_rgba8(image)
        if self._last_progress is not None:
            self.progressed.emit(FinalProgress(PHASE_SAVE, self._last_progress.fraction, self._last_progress.tile, self._last_progress.tiles,
                                               self._last_progress.samples_done, self._last_progress.samples_total, self._last_progress.elapsed,
                                               self._last_progress.remaining, self._last_progress.rate, self._last_progress.engine, "gpu", preview))
        self.preview_image = preview
        if i.settings.preview:
            self.last_frame = image
            return
        if not i.settings.save_incomplete and self.control.cancelled():
            return
        path = i.settings.frame_path(image.frame, i.animation.frames)
        if i.settings.unique_name:
            path = i.settings.unique(path)
        try:
            write_frame(image, path, i.settings, i.settings_text)
            self._written.append(path)
            if i.settings.save_parameters:
                write_parameters(path.with_suffix(PARAMS_SUFFIX), i.settings_text)
        except (OSError, ValueError) as exc:
            self._notes.append(f"could not write {path.name}: {exc}")

    # --- video -------------------------------------------------------------------------------------------------------------------
    def _encode(self, outcome: FragOutcome) -> None:
        """Run ffmpeg over the frames; problems become notes (the frames are on disk)."""
        i = self.inputs
        problems = i.settings.video_problems()
        if problems:
            self._notes.append("no video: " + "; ".join(problems))
            return
        frames = i.settings.frames(i.animation.frames)
        command = i.settings.ffmpeg_command(i.animation.fps, i.animation.frames, frames[0])
        try:
            process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, stdin=subprocess.DEVNULL, check=False)
        except OSError as exc:
            self._notes.append(f"ffmpeg could not be started: {exc}")
            return
        if process.returncode != 0:
            tail = " ".join((process.stdout or "").strip().splitlines()[-3:])
            self._notes.append(f"ffmpeg failed (exit code {process.returncode}): {tail or 'no output'}")
            return
        outcome.video = i.settings.video_path()
        self._notes.append(f"video written: {outcome.video}")
        if not i.settings.keep_frames:
            for path in outcome.frames:
                try:
                    path.unlink()
                except OSError:
                    pass
            outcome.frames = []
            self._notes.append("the frame images were removed after encoding")

    # --- the saved fragment (FragM's autosave) ----------------------------------------------------------------------------------
    def _fragment_path(self) -> Path:
        return self.inputs.settings.files_folder() / f"{safe_stem(self.inputs.name)}.frag"

    def _save_fragment(self) -> None:
        """`<name> Files/<name>.frag`: the text without its presets plus a `Default` preset of the settings; the includes beside it."""
        from ..files import FileManager
        from ..preprocessor import Preprocessor
        i = self.inputs
        folder = i.settings.files_folder()
        folder.mkdir(parents=True, exist_ok=True)
        text, dependencies = Preprocessor(FileManager()).create_autosave_fragment(i.text, None)
        lines = text.split("\n")
        head = lines[0] + "\n" if lines and lines[0].startswith("#version") else ""
        body = "\n".join(lines[1:]) if head else text
        final = (head + f"// Output generated from file: {i.name}\n// Created: {time.strftime('%c')}\n" + body.rstrip("\n")
                 + "\n\n#preset Default\n" + i.settings_text + "\n#endpreset\n")
        write_fragment(self._fragment_path(), final, None)
        self._notes.append(f"saved the fragment + settings as {self._fragment_path()}")
        if i.settings.include_files:
            for source in dependencies:
                try:
                    shutil.copyfile(source, folder / source.name)
                except OSError as exc:
                    self._notes.append(f"could not copy {source.name}: {exc}")


__all__ = ["FragRenderJob", "FragRenderInput", "FragOutcome"]
