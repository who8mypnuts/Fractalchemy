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

import time
from typing import Callable

import numpy as np

from ..fractal.scene import Flame
from .codegen import GeneratedProgram, generate
from .compiled import CompiledFlame
from .settings import RenderSettings, RenderStats
from .tonemap import FULLSCREEN_VERTEX_GLSL, TONEMAP_GLSL, ToneParams

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


class GpuEngine:
    """Owns the OpenGL context and the compiled programs; creates render jobs."""
    name = "GPU"

    def __init__(self):
        import moderngl
        self.gl = moderngl
        self.ctx = _create_context()
        self.renderer = self.ctx.info.get("GL_RENDERER", "OpenGL")
        self.ctx.enable(moderngl.PROGRAM_POINT_SIZE)
        self._tonemap = self.ctx.program(vertex_shader=FULLSCREEN_VERTEX_GLSL, fragment_shader=TONEMAP_GLSL)
        self._tonemap_vao = self.ctx.vertex_array(self._tonemap, [])
        self._programs: dict[str, tuple] = {}   # shader source -> compiled programs (structure cache)

    def start(self, flame: Flame, settings: RenderSettings) -> "GpuRenderJob":
        return GpuRenderJob(self, flame, settings)

    def programs(self, generated: GeneratedProgram):
        """Compiled (iterate, plot) programs, cached by source text."""
        key = generated.iterate_vertex + generated.plot_vertex
        if key not in self._programs:
            iterate = self.ctx.program(vertex_shader=generated.iterate_vertex, varyings=["out_state", "out_seed"])
            plot = self.ctx.program(vertex_shader=generated.plot_vertex, fragment_shader=_PLOT_FRAGMENT)
            self._programs[key] = (iterate, plot)
            if len(self._programs) > 32:
                self._programs.pop(next(iter(self._programs)))
        return self._programs[key]

    def close(self) -> None:
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


class GpuRenderJob:
    """One progressive render on the GPU; call `run_pass()` until `stats.finished`."""

    def __init__(self, engine: GpuEngine, flame: Flame, settings: RenderSettings):
        self.engine = engine
        self.ctx = engine.ctx
        self.settings = settings
        self.compiled = CompiledFlame.build(flame)
        self.generated = generate(self.compiled)
        self.iterate_prog, self.plot_prog = engine.programs(self.generated)
        self.coloring = flame.coloring
        self.ppu = flame.camera.pixels_per_unit(settings.width, settings.height)
        self.stats = RenderStats(engine=f"GPU ({engine.renderer})", passes_total=settings.passes,
                                 width=settings.width, height=settings.height, notes=list(self.compiled.notes))
        self._upload_params()
        self._create_population()
        self._create_targets()
        self._set_camera(flame)
        self._rng = np.random.default_rng(settings.seed)
        self._elapsed = 0.0
        self._fused = False
        self._closed = False

    # --- setup --------------------------------------------------------------
    def _upload_params(self) -> None:
        w, h = self.generated.params_texture_size
        self.params_tex = self.ctx.texture((w, h), 1, self.generated.params.tobytes(), dtype="f4")
        self.params_tex.filter = (self.engine.gl.NEAREST, self.engine.gl.NEAREST)
        self.palette_tex = self.ctx.texture((256, 1), 3, self.compiled.palette.astype(np.float32).tobytes(), dtype="f4")
        self.palette_tex.filter = (self.engine.gl.NEAREST, self.engine.gl.NEAREST)

    def _create_population(self) -> None:
        n = self.settings.points
        rng = np.random.default_rng(self.settings.seed)
        state = np.zeros((n, 5), dtype=np.uint32)
        state[:, :4] = np.column_stack([rng.uniform(-1, 1, n), rng.uniform(-1, 1, n), rng.random(n), np.zeros(n)]).astype(np.float32).view(np.uint32)
        state[:, 4] = rng.integers(1, 2 ** 32 - 1, n, dtype=np.uint32)
        self.buffers = [self.ctx.buffer(state.tobytes()), self.ctx.buffer(reserve=state.nbytes)]
        self.iterate_vaos = [self.ctx.vertex_array(self.iterate_prog, [(b, "4f 1u", "in_state", "in_seed")]) for b in self.buffers]
        self.plot_vaos = [self.ctx.vertex_array(self.plot_prog, [(b, "4f 1x4", "in_state")]) for b in self.buffers]
        self.current = 0

    def _create_targets(self) -> None:
        size = (self.settings.width, self.settings.height)
        self.hist_tex = self.ctx.texture(size, 4, dtype="f4")
        self.hist_tex.filter = (self.engine.gl.NEAREST, self.engine.gl.NEAREST)
        self.hist_fbo = self.ctx.framebuffer([self.hist_tex])
        self.hist_fbo.clear(0.0, 0.0, 0.0, 0.0)
        self.out_tex = self.ctx.texture(size, 4)
        self.out_fbo = self.ctx.framebuffer([self.out_tex])

    def _set_camera(self, flame: Flame) -> None:
        w, h = self.settings.width, self.settings.height
        a, b, c, d, e, f = flame.camera.pixel_transform(w, h)
        # pixel -> clip: x_clip = px / w * 2 - 1 ; y_clip = py / h * 2 - 1 (row 0 of the texture = top of the image)
        _set(self.plot_prog, "u_cam_x", (a * 2.0 / w, c * 2.0 / w, e * 2.0 / w - 1.0))
        _set(self.plot_prog, "u_cam_y", (b * 2.0 / h, d * 2.0 / h, f * 2.0 / h - 1.0))

    # --- rendering ----------------------------------------------------------
    def run_pass(self, cancelled: Callable[[], bool] = lambda: False) -> np.ndarray | None:
        """Iterate + plot enough draws for one pass, then tone-map and read back."""
        if self._closed:
            return None
        started = time.perf_counter()
        gl = self.engine.gl
        self.params_tex.use(0)
        self.palette_tex.use(1)
        _set(self.iterate_prog, "u_params", 0)
        _set(self.plot_prog, "u_params", 0)
        _set(self.plot_prog, "u_palette", 1)
        if not self._fused:
            self._iterate(self.settings.fuse)
            self._fused = True
        draws = max(1, -(-self.settings.samples_per_pass // self.settings.points))
        self.hist_fbo.use()
        self.ctx.viewport = (0, 0, self.settings.width, self.settings.height)
        self.ctx.enable(gl.BLEND)
        self.ctx.blend_func = gl.ONE, gl.ONE
        for _ in range(draws):
            if cancelled():
                return None
            self._iterate(1)
            _set(self.plot_prog, "u_salt", int(self._rng.integers(1, 2 ** 32 - 1)))
            self.plot_vaos[self.current].render(mode=gl.POINTS)
            self.stats.samples += self.settings.points
        self.ctx.disable(gl.BLEND)
        image = self._tonemap()
        self.stats.passes_done += 1
        self._elapsed += time.perf_counter() - started
        self.stats.seconds = self._elapsed
        self.stats.hits = self.stats.samples
        return image

    def _iterate(self, iterations: int) -> None:
        self.iterate_prog["u_iters"].value = iterations
        src, dst = self.current, 1 - self.current
        self.iterate_vaos[src].transform(self.buffers[dst], mode=self.engine.gl.POINTS)
        self.current = dst

    def _tonemap(self) -> np.ndarray:
        params = ToneParams.derive(self.coloring, self.ppu, self.stats.samples)
        self.out_fbo.use()
        self.ctx.viewport = (0, 0, self.settings.width, self.settings.height)
        self.hist_tex.use(2)
        prog = self.engine._tonemap
        _set(prog, "u_histogram", 2)
        for name, value in params.as_uniforms().items():
            _set(prog, name, value)
        self.engine._tonemap_vao.render(mode=self.engine.gl.TRIANGLES, vertices=3)
        data = self.out_fbo.read(components=4, dtype="f1")
        return np.frombuffer(data, dtype=np.uint8).reshape(self.settings.height, self.settings.width, 4).copy()

    def image(self) -> np.ndarray:
        return self._tonemap()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for obj in (*self.iterate_vaos, *self.plot_vaos, *self.buffers, self.params_tex, self.palette_tex,
                    self.hist_fbo, self.hist_tex, self.out_fbo, self.out_tex):
            obj.release()
