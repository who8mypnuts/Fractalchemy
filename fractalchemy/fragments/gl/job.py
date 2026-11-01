"""One progressive fragment render as a render-service job — FragM's `drawToFrameBufferObject` loop.

A `FragRequest` is the immutable payload (the translated sources, the uniform values, the surface policy) and a
`FragRenderSettings` says where and how much (size, subframe limit, time, tile, whether to clear or only redisplay).
Every `run_pass` draws `subframes_between_redraws + 1` subframes — bind the back buffer as `backbuffer`, set the
special uniforms, draw the fullscreen triangle into the front buffer, swap — then runs the display pass (the buffer
shader with `frontbuffer`, or a plain copy) into an RGBA8 target and reads it back for the GUI. `stats.passes_*`
count subframes; a subframe limit of 0 means "keep going" (the service's refine loop yields to other work between
passes). The first pass of a job also reports `BuildFacts`: compile time, the uniforms in use and the ones the
compiler removed.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from typing import Any, Callable

import numpy as np

from ... import config
from ...render.settings import RenderStats
from ..glsl_compat import ModernSource
from .passes import display, draw_subframe
from .program import Program
from .surfaces import Surface
from .uniforms import IDENTITY, tile_projection, unused_names

UNLIMITED = 1 << 30
MAX_SPLITS = 4


@dataclass(frozen=True)
class TileSpec:
    """Which tile of an `n × n` hi-res render this is (see `uniforms.tile_projection`)."""
    index: int = 0
    count: int = 1
    padding: float = 0.0


@dataclass(frozen=True)
class FragRequest:
    """The payload of one render: what to draw and with which values.

    Attributes:
        modern: The translated main program.
        buffer_modern: The translated buffer shader (None: the display pass is a plain copy).
        values: Uniform name → value (typed as the parameter model leaves them; the buffer shader takes the same dict).
        buffer: The `#buffer` type text.
        clear_on_change: False for `#define DontClearOnChange` fragments (the driver then submits with `clear=False`).
        subframes_between_redraws: `#define IterationsBetweenRedraws`.
        depth_to_alpha: The fragment has `DepthToAlpha` (output option for EXR).
        backbuffer_params: `#TexParameter backbuffer …` lines (filtering / wrapping of the accumulation textures).
        textures: Sampler uniform name → `TextureSpec` (the files to bind).
    """
    modern: ModernSource
    buffer_modern: ModernSource | None = None
    values: dict[str, Any] = field(default_factory=dict)
    buffer: str = ""
    clear_on_change: bool = True
    subframes_between_redraws: int = 0
    depth_to_alpha: bool = False
    backbuffer_params: dict[str, str] = field(default_factory=dict)
    textures: dict[str, object] = field(default_factory=dict)

    def copy(self) -> "FragRequest":
        """The service copies payloads; a request is immutable, so a shallow copy suffices."""
        return replace(self, values=dict(self.values))


@dataclass(frozen=True)
class FragRenderSettings:
    """Size and effort of one render.

    Attributes:
        width, height: The buffer size in pixels (already scaled for interactive renders).
        subframe_max: Stop after this many subframes (0 = unlimited; FragM's *Subframe Max*).
        subframes_per_pass: Subframes drawn per delivered image (≥ `subframes_between_redraws + 1`).
        time: The `time` uniform (seconds).
        tile: The tile of a hi-res render (the whole image by default).
        clear: Start the accumulation afresh (False: continue the key's surface — DontClearOnChange, a redisplay).
        redisplay_only: Draw no subframe; only re-run the display pass (a Post-group slider moved).
        surface_key: Which cached surface to use (one per document / viewport).
        depth_probe: A buffer pixel `(x, y)` (GL rows, y up) whose depth is read after each pass (`BuildFacts.probe_depth`)
            — FragM's `ZAtMXY` for the 3D point under the mouse.
        subframe_budget_ms: A subframe slower than this makes the job split the next ones into scissored tiles
            (the GPU watchdog mitigation; 0 = never split).
        gpu_load: The share of wall time the job may keep the GPU busy (1 = no limit): after every pass it idles
            for `elapsed · (1 − load) / load`, so a viewport that would pin the GPU at 100 % runs at this duty cycle.
    """
    width: int = 640
    height: int = 360
    subframe_max: int = 0
    subframes_per_pass: int = 1
    time: float = 0.0
    tile: TileSpec = TileSpec()
    clear: bool = True
    redisplay_only: bool = False
    surface_key: object = "viewport"
    depth_probe: tuple[int, int] | None = None
    subframe_budget_ms: float = config.FRAG_SUBFRAME_BUDGET_MS
    gpu_load: float = 1.0

    def scaled(self, factor: float) -> "FragRenderSettings":
        return replace(self, width=max(1, int(self.width * factor)), height=max(1, int(self.height * factor)))


@dataclass
class BuildFacts:
    """What building the program told us (delivered with the first pass through `RenderStats.facts`).

    Attributes:
        compile_ms: Milliseconds the programs took to compile and link (the cached figure when they were already built).
        active: The fragment's uniforms the linked program kept.
        buffer_active: The buffer shader's uniforms (a change to one of these alone needs only the display pass).
        unused: The parameters the compiler optimised away (their widgets hide unless locked).
        version: The GLSL version compiled.
        notes: The compatibility layer's notes plus the engine's remarks.
        renderer: The GL renderer string.
        probe_depth: The depth buffer value at the settings' `depth_probe` after the last pass (None: no probe).
        tiled: Subframes are drawn as `tiled × tiled` scissored rectangles (1 = whole draws) — the watchdog mitigation.
    """
    compile_ms: float = 0.0
    active: list[str] = field(default_factory=list)
    buffer_active: list[str] = field(default_factory=list)
    unused: list[str] = field(default_factory=list)
    version: int = 0
    notes: list[str] = field(default_factory=list)
    renderer: str = ""
    probe_depth: float | None = None
    tiled: int = 1


class FragJob:
    """The service's job protocol for one fragment render (see the module docstring).

    Args:
        engine: The owning `FragEngine` (context, program cache, surfaces).
        request: What to draw.
        settings: Where and how much.
    """

    def __init__(self, engine, request: FragRequest, settings: FragRenderSettings):
        self.engine = engine
        self.ctx = engine.ctx
        self.request = request
        self.settings = settings
        self.stats = RenderStats(engine.name, 0, settings.subframe_max or UNLIMITED, 0, 0, 0.0, settings.width, settings.height)
        self.program: Program | None = None
        self.buffer_program: Program | None = None
        self.surface: Surface | None = None
        self._out_tex = self.ctx.texture((settings.width, settings.height), 4)
        self._out_fbo = self.ctx.framebuffer([self._out_tex])
        self._elapsed = 0.0
        self._closed = False
        self._splits = 1

    # --- set-up -------------------------------------------------------------------------------------------------------
    def _prepare(self) -> None:
        """Build (or fetch) the programs, take the surface, record the facts; raises `ShaderBuildError`."""
        self.program, _cached = self.engine.build(self.request.modern)
        if self.request.buffer_modern is not None:
            self.buffer_program, _ = self.engine.build(self.request.buffer_modern)
        compile_ms = sum(p.compile_ms for p in (self.program, self.buffer_program) if p is not None)
        s = self.settings
        self.surface = self.engine.surfaces.get(s.surface_key, s.width, s.height, self.request.buffer, clear=s.clear)
        self.surface.apply_params(self.request.backbuffer_params)
        facts = BuildFacts(compile_ms=compile_ms, active=self.program.user_uniform_names(),
                           unused=unused_names(self.program, list(self.request.values)), version=self.request.modern.version,
                           notes=list(self.request.modern.notes), renderer=self.engine.renderer)
        facts.notes += self.engine.textures.take_problems()
        if self.buffer_program is not None:       # a parameter used only by the buffer shader is not unused
            facts.buffer_active = self.buffer_program.user_uniform_names()
            facts.unused = [n for n in facts.unused if n not in self.buffer_program.uniforms]
        self.stats.facts = facts
        self.stats.passes_done = self.surface.subframe

    # --- the service protocol -------------------------------------------------------------------------------------------
    def run_pass(self, cancelled: Callable[[], bool] = lambda: False) -> np.ndarray | None:
        """Draw the subframes of one pass and return the displayed image (None when cancelled between subframes)."""
        if self._closed:
            return None
        started = time.perf_counter()
        if self.program is None:
            self._prepare()
        if not self.settings.redisplay_only:
            for _ in range(self._subframes_this_pass()):
                if cancelled():
                    return None
                self._draw_subframe()
        else:
            self.stats.passes_total = self.stats.passes_done      # one display pass, then done
        image = self._display()
        self.stats.facts.notes += self.engine.textures.take_problems()     # a texture that failed to load this pass
        if self.settings.depth_probe is not None:
            self.stats.facts.probe_depth = self.surface.depth_at(*self.settings.depth_probe)
        elapsed = time.perf_counter() - started
        self._elapsed += elapsed
        self.stats.seconds = self._elapsed
        self.stats.samples = self.stats.hits = self.surface.subframe * self.settings.width * self.settings.height
        self._throttle(elapsed, cancelled)
        return image

    def _throttle(self, elapsed: float, cancelled: Callable[[], bool]) -> None:
        """Idle after the pass so the GPU's duty cycle stays at `settings.gpu_load` (in short slices, to stay cancellable)."""
        load = min(1.0, max(0.05, float(self.settings.gpu_load)))
        if load >= 1.0 or self.stats.finished:
            return
        deadline = time.perf_counter() + elapsed * (1.0 - load) / load
        while time.perf_counter() < deadline and not cancelled():
            time.sleep(min(0.02, max(0.0, deadline - time.perf_counter())))

    def _subframes_this_pass(self) -> int:
        per_pass = max(1, self.settings.subframes_per_pass, self.request.subframes_between_redraws + 1)
        remaining = self.stats.passes_total - self.surface.subframe
        return max(1, min(per_pass, remaining))

    def _draw_subframe(self) -> None:
        """FragM's `drawFragmentProgram`: back buffer in, front buffer out, depth always written; timed for the watchdog."""
        s = self.settings
        projection = tile_projection(s.tile.index, s.tile.count, s.tile.padding) if s.tile.count > 1 else IDENTITY
        started = time.perf_counter()
        draw_subframe(self.engine, self.program, self.surface, self.request, s.time, projection, self._splits)
        if s.subframe_budget_ms > 0:
            self.ctx.finish()
            self._watch((time.perf_counter() - started) * 1000.0)
        self.stats.passes_done = self.surface.subframe

    def _watch(self, subframe_ms: float) -> None:
        """Split the next subframes finer when this one was over budget (2×2, 3×3 … up to `MAX_SPLITS`)."""
        if subframe_ms <= self.settings.subframe_budget_ms or self._splits >= MAX_SPLITS:
            return
        self._splits += 1
        self.stats.facts.tiled = self._splits
        self.stats.notes.append(f"subframe took {subframe_ms:.0f} ms: drawing in {self._splits}×{self._splits} tiles to stay clear of the GPU watchdog")

    def _display(self) -> np.ndarray:
        """The display pass into the RGBA8 target: the buffer shader (tone mapping) or a plain copy, then read back."""
        s = self.settings
        display(self.engine, self.buffer_program, self.surface, self.request, self._out_fbo, s.width, s.height, s.time)
        data = self._out_fbo.read(components=4, dtype="f1")
        return np.frombuffer(data, dtype=np.uint8).reshape(s.height, s.width, 4)[::-1].copy()

    def image(self) -> np.ndarray | None:
        """The current accumulation displayed (None before the first pass)."""
        return None if self.surface is None else self._display()

    def close(self) -> None:
        """Free the job's own GPU objects (the surface and the programs belong to the engine)."""
        if self._closed:
            return
        self._closed = True
        self._out_fbo.release()
        self._out_tex.release()


__all__ = ["FragJob", "FragRequest", "FragRenderSettings", "TileSpec", "BuildFacts", "UNLIMITED"]
