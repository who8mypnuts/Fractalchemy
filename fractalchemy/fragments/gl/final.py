"""The hi-res / animation renderer — FragM's `tileBasedRender` / `renderTile` on an engine of its own.

For every frame of the range: the camera path and the easing curves set the frame's values; every tile gets a fresh
surface and `subframes` subframes drawn with the tile's projection matrix (FragM's `renderTile`), then the display
pass (the buffer shader) into a float target; the tile's centre (the padding cropped) lands in the assembled float
image — and, with *depth to alpha*, so does its depth buffer. The float image is handed to the caller per frame
(`frame_done`) for writing: 8 / 16-bit formats through the host's writers, OpenEXR as float `R G B` with `A` (or `Z`),
which is what FragM writes. Cancel and pause are checked between subframes through a `RenderControl`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np

from ...render.control import RenderControl
from ...render.exr import write_exr
from ...render.final_engine import PHASE_CANCELLED, PHASE_DONE, PHASE_RENDER, PHASE_SAVE, FinalProgress
from ...render.output import SaveOptions, output_format, save_image
from ... import config
from ..animation import AnimationSettings, frame_values
from ..document_format import IMAGE_KEY
from ..render_settings import FragFinalSettings
from .job import FragRequest
from .passes import display, draw_subframe
from .surfaces import Surface
from .uniforms import tile_projection

PROGRESS_INTERVAL = 0.25


@dataclass
class FrameImage:
    """One assembled frame.

    Attributes:
        frame: The frame number.
        rgba: `(H, W, 4)` float32 — the display pass's output (tone-mapped colour, alpha).
        depth: `(H, W)` float32 depth buffer values when *depth to alpha* was asked, else None.
    """
    frame: int
    rgba: np.ndarray
    depth: np.ndarray | None = None


@dataclass
class FragFinalResult:
    """What the renderer reports when it stops (duck-typed like the flame renderer's result for the progress panel)."""
    complete: bool
    seconds: float
    samples: int
    engine: str
    frames_rendered: int = 0
    paths: list[Path] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


class FragFinalRenderer:
    """Renders the frames / tiles of a hi-res job (see the module docstring).

    Args:
        engine: A `FragEngine` owned by the calling thread.
        request: The fragment program and its base values.
        state: The parameter state (for per-frame values; copied).
        settings: The render plan.
        animation: The clock (fps, length, looping path).
        camera_path: The keyframe path, or None.
        curves: The easing curves.
        auto_focus: The fragment has *AutoFocus*.
        control: Cancel / pause flags.
        blend: The keyframe parameter blend (the *all* interpolation mode), or None.
    """

    def __init__(self, engine, request: FragRequest, state, settings: FragFinalSettings, animation: AnimationSettings,
                 camera_path, curves, auto_focus: bool, control: RenderControl | None = None, blend=None):
        self.engine = engine
        self.blend = blend
        self.request = request
        self.state = state.copy()
        self.settings = settings
        self.animation = animation
        self.path = camera_path
        self.curves = list(curves)
        self.auto_focus = auto_focus
        self.control = control or RenderControl()
        self._steps_done = 0
        self._started = 0.0
        self._last_report = 0.0

    # --- the loop ---------------------------------------------------------------------------------------------------------
    def run(self, progress: Callable[[FinalProgress], None] | None = None, frame_done: Callable[[FrameImage], None] | None = None
            ) -> FragFinalResult:
        """Render every frame; `frame_done` receives each assembled frame, `progress` a report a few times a second."""
        self._started = time.perf_counter()
        frames = self.settings.frames(self.animation.frames)
        total_steps = self.settings.total_steps(self.animation.frames)
        program, _ = self.engine.build(self.request.modern)
        buffer_program = self.engine.build(self.request.buffer_modern)[0] if self.request.buffer_modern is not None else None
        rendered = 0
        complete = True
        for frame in frames:
            values = self._values_for(frame)
            request = self.request.copy()
            request.values.update(values)
            image = self._render_frame(frame, request, program, buffer_program, total_steps, progress)
            if image is None:
                complete = False
                break
            rendered += 1
            if frame_done is not None:
                frame_done(image)
        seconds = time.perf_counter() - self._started - self.control.paused_seconds
        width, height = self.settings.image_size
        if progress is not None:
            progress(self._progress(PHASE_DONE if complete else PHASE_CANCELLED, total_steps, 0, 0, None))
        return FragFinalResult(complete, seconds, self._steps_done * width * height // max(1, self.settings.tile_count), self.engine.name, rendered)

    def _values_for(self, frame: int) -> dict:
        """The frame's camera and eased values on top of the base state."""
        if self.path is None and not self.curves and self.blend is None:
            return {}
        return frame_values(frame, self.state, self.path, self.curves, self.auto_focus, self.blend)

    def _render_frame(self, frame: int, request, program, buffer_program, total_steps: int, progress) -> FrameImage | None:
        s = self.settings
        width, height = s.image_size
        inner_w, inner_h = s.inner_tile
        rgba = np.zeros((height, width, 4), dtype=np.float32)
        depth = np.zeros((height, width), dtype=np.float32) if s.depth_to_alpha else None
        time_value = self.animation.time_of(frame)
        for index in range(s.tile_count):
            tile = self._render_tile(index, request, program, buffer_program, time_value, frame, total_steps, progress)
            if tile is None:
                return None
            tile_rgba, tile_depth = tile
            x0 = (s.tile_width - inner_w) // 2
            y0 = (s.tile_height - inner_h) // 2
            dx, dy = index // s.tiles, (s.tiles - 1) - index % s.tiles           # FragM's placement
            rgba[dy * inner_h:(dy + 1) * inner_h, dx * inner_w:(dx + 1) * inner_w] = tile_rgba[y0:y0 + inner_h, x0:x0 + inner_w]
            if depth is not None and tile_depth is not None:
                depth[dy * inner_h:(dy + 1) * inner_h, dx * inner_w:(dx + 1) * inner_w] = tile_depth[y0:y0 + inner_h, x0:x0 + inner_w]
        return FrameImage(frame, rgba, depth)

    def _render_tile(self, index: int, request, program, buffer_program, time_value: float, frame: int, total_steps: int, progress):
        s = self.settings
        surface = Surface(self.engine.ctx, s.tile_width, s.tile_height, request.buffer)
        surface.apply_params(request.backbuffer_params)
        target_tex = self.engine.ctx.texture((s.tile_width, s.tile_height), 4, dtype="f4")
        target_fbo = self.engine.ctx.framebuffer([target_tex])
        try:
            projection = tile_projection(index, s.tiles, s.padding)
            for _ in range(max(1, s.subframes)):
                if not self.control.wait_if_paused() or self.control.cancelled():
                    return None
                draw_subframe(self.engine, program, surface, request, time_value, projection)
                self._steps_done += 1
                self._maybe_report(progress, total_steps, index, frame)
            display(self.engine, buffer_program, surface, request, target_fbo, s.tile_width, s.tile_height, time_value)
            data = target_fbo.read(components=4, dtype="f4")
            rgba = np.frombuffer(data, dtype=np.float32).reshape(s.tile_height, s.tile_width, 4)[::-1].copy()
            depth = surface.read_depth() if s.depth_to_alpha else None
            return rgba, depth
        finally:
            target_fbo.release()
            target_tex.release()
            surface.release()

    # --- progress ---------------------------------------------------------------------------------------------------------------
    def _maybe_report(self, progress, total_steps: int, tile: int, frame: int) -> None:
        now = time.perf_counter()
        if progress is None or now - self._last_report < PROGRESS_INTERVAL:
            return
        self._last_report = now
        progress(self._progress(PHASE_RENDER, total_steps, tile, frame, None))

    def _progress(self, phase: str, total_steps: int, tile: int, frame: int, preview) -> FinalProgress:
        elapsed = time.perf_counter() - self._started - self.control.paused_seconds
        fraction = self._steps_done / max(1, total_steps)
        rate = self._steps_done / elapsed if elapsed > 0 else 0.0
        remaining = (total_steps - self._steps_done) / rate if rate > 0 else None
        width, height = self.settings.image_size
        return FinalProgress(phase, fraction, tile + 1, self.settings.tile_count, self._steps_done * width * height,
                             total_steps * width * height, elapsed, remaining, rate * width * height / max(1, self.settings.tile_count),
                             f"{self.engine.name} · frame {frame}", "gpu", preview)


# --- writing -----------------------------------------------------------------------------------------------------------------
def write_frame(image: FrameImage, path: Path, settings: FragFinalSettings, settings_text: str) -> Path:
    """Write an assembled frame: EXR as float `R G B` + `A` or `Z` (FragM's layout), everything else through the host's writers."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if settings.output_format == "exr":
        rgba = image.rgba
        channels = {"R": rgba[..., 0], "G": rgba[..., 1], "B": rgba[..., 2]}
        if image.depth is not None:
            channels["Z"] = image.depth
        else:
            channels["A"] = rgba[..., 3]
        attributes = {"writer": f"{config.APP_NAME} {config.APP_VERSION}", "fractalchemy:source": "Fragments"}
        if settings.embed_parameters and settings_text:
            attributes[IMAGE_KEY] = settings_text
        write_exr(path, channels, attributes, half=settings.depth <= 16)
        return path
    fmt = output_format(settings.output_format)
    data = (np.clip(image.rgba, 0.0, 1.0) * 65535.0 + 0.5).astype(np.uint16)
    options = SaveOptions(depth=settings.depth, transparent=False, parameters=settings_text if settings.embed_parameters else "",
                          parameters_key=IMAGE_KEY)
    save_image(data, path, fmt, options)
    return path


def to_display_rgba8(image: FrameImage, max_side: int = 1024) -> np.ndarray:
    """A preview-sized RGBA8 copy of a frame (for the progress panel)."""
    rgba = np.clip(image.rgba, 0.0, 1.0)
    height, width = rgba.shape[:2]
    step = max(1, int(np.ceil(max(width, height) / max_side)))
    small = rgba[::step, ::step]
    out = (small * 255.0 + 0.5).astype(np.uint8)
    out[..., 3] = 255
    return np.ascontiguousarray(out)


__all__ = ["FragFinalRenderer", "FragFinalResult", "FrameImage", "write_frame", "to_display_rgba8", "PHASE_SAVE"]
