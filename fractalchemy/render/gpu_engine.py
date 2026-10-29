"""GPU preview engine (moderngl / OpenGL 3.3).

Pipeline per pass:

1. **iterate** — a vertex shader advances every point of the population through one
   chaos-game step; transform feedback writes the new state into the other buffer.
2. **plot** — the population is drawn as GL_POINTS with additive blending into an
   RGBA32F histogram (rgb = palette colour × opacity, a = opacity).
3. **tone map** — a fullscreen pass turns the histogram into RGBA8, which is read back.

Everything happens on whichever thread created the engine (OpenGL contexts are
thread-bound), so the render service owns one engine on its worker thread.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Callable

import numpy as np

from ..fractal.scene import Camera, Flame
from .codegen import STATE_BYTES, GeneratedProgram, generate
from .compiled import CompiledFlame
from .filtering import bucket_transform
from .projection import glsl_uniforms
from .settings import RenderSettings, RenderStats
from .tonemap import FULLSCREEN_VERTEX_GLSL, SCALE_GLSL, TONEMAP_GLSL, ToneParams, curve_luts, filter_uniforms

log = logging.getLogger(__name__)

_probe_result: tuple[bool, str] | None = None


def gpu_available() -> tuple[bool, str]:
    """(True, renderer name) if a standalone OpenGL context can be created here, else (False, reason).

    The probe runs once per process; its context is released immediately.
    """
    global _probe_result
    if _probe_result is None:
        try:
            ctx = _create_context()
            _probe_result = (True, ctx.info.get("GL_RENDERER", "OpenGL"))
            ctx.release()
        except Exception as exc:  # noqa: BLE001 - any failure means "no GPU path"
            _probe_result = (False, str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__)
    return _probe_result


def _create_context():
    import moderngl
    try:
        return moderngl.create_standalone_context(require=330)
    except Exception:  # noqa: BLE001 - retry headless (EGL) before giving up
        return moderngl.create_standalone_context(require=330, backend="egl")


def create_context():
    """Public alias used by tests and callers that need a standalone OpenGL context."""
    return _create_context()


class ShaderBuildError(RuntimeError):
    """The GPU driver rejected a generated shader; `report` is the diagnostics file written (or None)."""

    def __init__(self, message: str, report: Path | None):
        lines = [ln.strip() for ln in message.splitlines() if ln.strip()]
        first = next((ln for ln in lines if "error" in ln.lower() and "failed" not in ln.lower()), lines[0] if lines else "shader build failed")
        super().__init__(first + (f" (details in {report})" if report else ""))
        self.log = message
        self.report = report


def glsl_failure_dir() -> Path:
    from ..formulas.loader import cache_dir
    return cache_dir() / "glsl-failures"


def _dump_failure(generated: GeneratedProgram, exc: Exception, renderer: str) -> Path | None:
    """Write the shader sources and the compiler output for a failed build; returns the report path."""
    try:
        folder = glsl_failure_dir()
        folder.mkdir(parents=True, exist_ok=True)
        report = folder / time.strftime("%Y%m%d-%H%M%S.txt")
        report.write_text(f"renderer: {renderer}\n\n=== compiler output ===\n{exc}\n\n=== iterate shader ===\n{generated.iterate_vertex}\n\n"
                          f"=== plot shader ===\n{generated.plot_vertex}\n", encoding="utf-8")
        log.warning("GPU shader build failed on %s; sources and compiler log written to %s", renderer, report)
        return report
    except OSError:
        log.warning("GPU shader build failed on %s: %s", renderer, str(exc).splitlines()[0] if str(exc) else exc)
        return None


class GpuEngine:
    """Owns the OpenGL context and the compiled programs; creates render jobs."""
    name = "GPU"

    def __init__(self):
        import moderngl
        self.gl = moderngl
        self.ctx = _create_context()
        self.renderer = self.ctx.info.get("GL_RENDERER", "OpenGL")
        self.ctx.enable(moderngl.PROGRAM_POINT_SIZE)
        self._scale = self.ctx.program(vertex_shader=FULLSCREEN_VERTEX_GLSL, fragment_shader=SCALE_GLSL)
        self._scale_vao = self.ctx.vertex_array(self._scale, [])
        self._tonemap = self.ctx.program(vertex_shader=FULLSCREEN_VERTEX_GLSL, fragment_shader=TONEMAP_GLSL)
        self._tonemap_vao = self.ctx.vertex_array(self._tonemap, [])
        self._programs: dict[str, tuple] = {}   # shader source -> compiled programs (structure cache)

    def start(self, flame: Flame, settings: RenderSettings):
        """A new progressive render job for `flame` (a solid render when the settings carry a 3D scene)."""
        if settings.solid is not None:
            from .gpu_solid import SolidGpuJob
            return SolidGpuJob(self, flame, settings, settings.solid)
        return GpuRenderJob(self, flame, settings)

    def programs(self, generated: GeneratedProgram, plot_fragment: str | None = None):
        """Compiled (iterate, plot) programs, cached by source text (`plot_fragment`: another fragment shader for the
        plot program, the solid renderer's G-buffer writer).

        Raises:
            ShaderBuildError: The driver rejected the generated GLSL; the sources and the compiler log
                are written to `glsl_failure_dir()` so the problem can be reported and reproduced.
        """
        fragment = plot_fragment or _PLOT_FRAGMENT
        key = generated.iterate_vertex + generated.plot_vertex + fragment
        if key not in self._programs:
            try:
                iterate = self.ctx.program(vertex_shader=generated.iterate_vertex, varyings=["out_state", "out_xi", "out_seed"])
                plot = self.ctx.program(vertex_shader=generated.plot_vertex, fragment_shader=fragment)
            except Exception as exc:  # noqa: BLE001 - moderngl.Error carries the compiler log
                raise ShaderBuildError(str(exc), _dump_failure(generated, exc, self.renderer)) from exc
            self._programs[key] = (iterate, plot)
            if len(self._programs) > 32:
                self._programs.pop(next(iter(self._programs)))
        return self._programs[key]

    def close(self) -> None:
        """Release the OpenGL context."""
        self.ctx.release()


def _set(program, name: str, value) -> None:
    """Set a uniform, ignoring ones the GLSL compiler optimised away."""
    uniform = program.get(name, None)
    if uniform is not None:
        uniform.value = value


_PLOT_FRAGMENT = """
#version 330
in vec4 v_color;
out vec4 f_color;
void main() { f_color = v_color; }
"""


class GpuPopulation:
    """A point population with its flame baked in: iterate it, plot it into whatever framebuffer is bound.

    Shared by the preview job and the final renderer's GPU sampler. The plot target and the
    camera are the caller's business: `set_pixel_transform` takes the affine mapping fractal
    coordinates to pixels of a `width × height` target (row 0 at the top).
    """

    def __init__(self, engine: GpuEngine, compiled: CompiledFlame, points: int, seed: int,
                 camera: Camera | None = None, generated: GeneratedProgram | None = None, plot_fragment: str | None = None):
        self.engine = engine
        self.ctx = engine.ctx
        self.compiled = compiled
        self.points = points
        self.seed = seed
        self.camera = camera if camera is not None else Camera()
        self.generated = generated if generated is not None else generate(compiled)
        self.iterate_prog, self.plot_prog = engine.programs(self.generated, plot_fragment)
        self._rng = np.random.default_rng(seed)
        self._upload_params()
        self._create_population(seed)
        self._released = False

    def _upload_params(self) -> None:
        w, h = self.generated.params_texture_size
        self.params_tex = self.ctx.texture((w, h), 1, self.generated.params.tobytes(), dtype="f4")
        self.params_tex.filter = (self.engine.gl.NEAREST, self.engine.gl.NEAREST)
        self.palette_tex = self.ctx.texture((256, 1), 3, self.compiled.palette.astype(np.float32).tobytes(), dtype="f4")
        self.palette_tex.filter = (self.engine.gl.NEAREST, self.engine.gl.NEAREST)

    def _create_population(self, seed: int) -> None:
        n = self.points
        rng = np.random.default_rng(seed)
        state = np.zeros((n, STATE_BYTES // 4), dtype=np.uint32)
        # (x, y, z, colour) as float32 bits, then the last xform index and the RNG seed
        state[:, :4] = np.column_stack([rng.uniform(-1, 1, n), rng.uniform(-1, 1, n), np.zeros(n),
                                        rng.random(n)]).astype(np.float32).view(np.uint32)
        state[:, 4] = 0
        state[:, 5] = rng.integers(1, 2 ** 32 - 1, n, dtype=np.uint32)
        self.buffers = [self.ctx.buffer(state.tobytes()), self.ctx.buffer(reserve=state.nbytes)]
        self.iterate_vaos = [self.ctx.vertex_array(self.iterate_prog,
                                                   [(b, "4f 1u 1u", "in_state", "in_xi", "in_seed")])
                             for b in self.buffers]
        self.plot_vaos = [self.ctx.vertex_array(self.plot_prog, [(b, "4f 1u 1x4", "in_state", "in_xi")])
                          for b in self.buffers]
        self.current = 0

    def set_pixel_transform(self, affine, width: int, height: int) -> None:
        """Camera for plotting: `affine` maps fractal space to pixels of a `width × height` target."""
        a, b, c, d, e, f = affine
        # pixel -> clip: x_clip = px / w * 2 - 1 ; y_clip = py / h * 2 - 1 (row 0 of the texture = top of the image)
        _set(self.plot_prog, "u_cam_x", (a * 2.0 / width, c * 2.0 / width, e * 2.0 / width - 1.0))
        _set(self.plot_prog, "u_cam_y", (b * 2.0 / height, d * 2.0 / height, f * 2.0 / height - 1.0))
        for name, value in glsl_uniforms(self.camera).items():
            _set(self.plot_prog, name, value)

    def bind(self) -> None:
        """Bind the parameter and palette textures (once per batch of draws)."""
        self.params_tex.use(0)
        self.palette_tex.use(1)
        _set(self.iterate_prog, "u_params", 0)
        _set(self.plot_prog, "u_params", 0)
        _set(self.plot_prog, "u_palette", 1)

    def iterate(self, iterations: int) -> None:
        """Advance every point `iterations` chaos-game steps (transform feedback ping-pong)."""
        self.iterate_prog["u_iters"].value = iterations
        src, dst = self.current, 1 - self.current
        self.iterate_vaos[src].transform(self.buffers[dst], mode=self.engine.gl.POINTS)
        self.current = dst

    def plot(self) -> None:
        """Draw the population as points into the bound framebuffer (additive blending must be enabled)."""
        _set(self.plot_prog, "u_salt", int(self._rng.integers(1, 2 ** 32 - 1)))
        self.plot_vaos[self.current].render(mode=self.engine.gl.POINTS)

    def release(self) -> None:
        """Free the GPU objects."""
        if self._released:
            return
        self._released = True
        for obj in (*self.iterate_vaos, *self.plot_vaos, *self.buffers, self.params_tex, self.palette_tex):
            obj.release()


class GpuRenderJob:
    """One progressive render on the GPU; call `run_pass()` until `stats.finished`."""

    def __init__(self, engine: GpuEngine, flame: Flame, settings: RenderSettings):
        self.engine = engine
        self.ctx = engine.ctx
        self.settings = settings
        self.compiled = CompiledFlame.build(flame)
        self.population = GpuPopulation(engine, self.compiled, settings.points, settings.seed, flame.camera)
        self.coloring = flame.coloring
        self.ppu = flame.camera.pixels_per_unit(settings.width, settings.height)
        self.stats = RenderStats(engine=f"GPU ({engine.renderer})", passes_total=settings.passes,
                                 width=settings.width, height=settings.height, notes=list(self.compiled.notes),
                                 samples_target=settings.samples_target)
        self._upload_curves()
        self._create_targets()
        s = settings
        self.population.set_pixel_transform(
            bucket_transform(flame.camera.pixel_transform(s.width, s.height), s.oversample, s.gutter),
            *self.bucket_size)
        self._elapsed = 0.0
        self._fused = False
        self._closed = False

    # --- setup --------------------------------------------------------------
    def _upload_curves(self) -> None:
        luts = curve_luts(self.coloring.curves)
        self.has_curves = luts is not None
        table = np.zeros((2, 256, 4), dtype=np.float32)
        if luts is not None:
            table[0, :, :] = luts[:4].T          # row 0: overall, red, green, blue
            table[1, :, 0] = luts[4]             # row 1: alpha
        self.curves_tex = self.ctx.texture((256, 2), 4, table.tobytes(), dtype="f4")
        self.curves_tex.filter = (self.engine.gl.LINEAR, self.engine.gl.LINEAR)
        self.curves_tex.repeat_x = self.curves_tex.repeat_y = False

    def _create_targets(self) -> None:
        self.bucket_size = self.settings.bucket_size    # supersampled + gutter (Apophysis oversample / filter)
        self.hist_tex = self.ctx.texture(self.bucket_size, 4, dtype="f4")
        self.hist_tex.filter = (self.engine.gl.NEAREST, self.engine.gl.NEAREST)
        self.hist_fbo = self.ctx.framebuffer([self.hist_tex])
        self.hist_fbo.clear(0.0, 0.0, 0.0, 0.0)
        self.scaled_tex = self.ctx.texture(self.bucket_size, 4, dtype="f4")
        self.scaled_tex.filter = (self.engine.gl.NEAREST, self.engine.gl.NEAREST)
        self.scaled_fbo = self.ctx.framebuffer([self.scaled_tex])
        self.out_tex = self.ctx.texture((self.settings.width, self.settings.height), 4)
        self.out_fbo = self.ctx.framebuffer([self.out_tex])

    # --- rendering ----------------------------------------------------------
    def run_pass(self, cancelled: Callable[[], bool] = lambda: False) -> np.ndarray | None:
        """Iterate + plot enough draws for one pass, then tone-map and read back."""
        if self._closed:
            return None
        started = time.perf_counter()
        gl = self.engine.gl
        self.population.bind()
        if not self._fused:
            self.population.iterate(self.settings.fuse)
            self._fused = True
        wanted = self.settings.next_pass_samples(self.stats.passes_done, self.stats.samples)
        draws = max(1, -(-wanted // self.settings.points))
        self.hist_fbo.use()
        self.ctx.viewport = (0, 0, *self.bucket_size)
        self.ctx.enable(gl.BLEND)
        self.ctx.blend_func = gl.ONE, gl.ONE
        for _ in range(draws):
            if cancelled():
                return None
            self.population.iterate(1)
            self.population.plot()
            self.stats.samples += self.settings.points
        self.ctx.disable(gl.BLEND)
        image = self._tonemap()
        self.stats.passes_done += 1
        self._elapsed += time.perf_counter() - started
        self.stats.seconds = self._elapsed
        self.stats.hits = self.stats.samples
        return image

    def _tonemap(self) -> np.ndarray:
        s = self.settings
        params = ToneParams.derive(self.coloring, self.ppu, self.stats.samples, s.oversample)
        uniforms = params.as_uniforms() | filter_uniforms(s.oversample, s.filter_radius)
        # pass 1: log-density scale every bucket
        self.scaled_fbo.use()
        self.ctx.viewport = (0, 0, *self.bucket_size)
        self.hist_tex.use(2)
        prog = self.engine._scale
        _set(prog, "u_histogram", 2)
        for name in ("u_k1", "u_k2"):
            _set(prog, name, uniforms[name])
        self.engine._scale_vao.render(mode=self.engine.gl.TRIANGLES, vertices=3)
        # pass 2: gather the buckets of each pixel through the spatial filter, then gamma / vibrancy / background
        self.out_fbo.use()
        self.ctx.viewport = (0, 0, s.width, s.height)
        self.scaled_tex.use(3)
        self.curves_tex.use(4)
        prog = self.engine._tonemap
        _set(prog, "u_scaled", 3)
        _set(prog, "u_curves", 4)
        _set(prog, "u_has_curves", self.has_curves)
        for name, value in uniforms.items():
            _set(prog, name, value)
        self.engine._tonemap_vao.render(mode=self.engine.gl.TRIANGLES, vertices=3)
        data = self.out_fbo.read(components=4, dtype="f1")
        return np.frombuffer(data, dtype=np.uint8).reshape(self.settings.height, self.settings.width, 4).copy()

    def image(self) -> np.ndarray:
        """The current histogram tone-mapped to RGBA8."""
        return self._tonemap()

    def close(self) -> None:
        """Free the GPU objects (idempotent)."""
        if self._closed:
            return
        self._closed = True
        self.population.release()
        for obj in (self.curves_tex, self.hist_fbo, self.hist_tex, self.scaled_fbo, self.scaled_tex,
                    self.out_fbo, self.out_tex):
            obj.release()
