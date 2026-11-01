"""The fragment engine: the OpenGL context, the program cache, the surfaces — and the render service's entry point.

    engine = FragEngine()                       # on the thread that will render
    job = engine.start(request, settings)       # the service protocol; job.run_pass(...) → RGBA8 image

`build()` compiles a translated program once per source text and keeps it (FragM recompiles on every build; the
cache makes flipping between presets that lock different values cheap). A rejected shader raises the flame
engine's `ShaderBuildError` carrying the mapped diagnostics and the report file in the GLSL-failures folder.
`FragEngineFactory` plugs the engine into a `RenderService`.
"""

from __future__ import annotations

import time

import numpy as np

from ...render.gpu_engine import ShaderBuildError, create_context, write_failure_report
from ..glsl_compat import ModernSource
from .diagnostics import Diagnostic, parse_log
from .program import Program
from .surfaces import SurfaceCache
from .textures import TextureCache

PROGRAM_CACHE_LIMIT = 24
TRIANGLE = np.array([-1.0, -1.0, 0.0, 1.0, 3.0, -1.0, 0.0, 1.0, -1.0, 3.0, 0.0, 1.0], dtype=np.float32)   # FragM's points[9] + w
COPY_VERTEX = """#version 330 core
layout(location = 0) in vec4 vertex_position;
out vec2 v_uv;
void main() { gl_Position = vertex_position; v_uv = vertex_position.xy * 0.5 + 0.5; }
"""
COPY_FRAGMENT = """#version 330 core
in vec2 v_uv;
uniform sampler2D frontbuffer;
out vec4 fragColor;
void main() { fragColor = clamp(texture(frontbuffer, v_uv), 0.0, 1.0); }
"""


class FragBuildError(ShaderBuildError):
    """A fragment program the driver rejected, with the diagnostics mapped to the original source."""

    def __init__(self, diagnostics: list[Diagnostic], log_text: str, report):
        errors = [d for d in diagnostics if d.severity == "error"] or diagnostics
        message = errors[0].text() if errors else (log_text.strip().splitlines() or ["shader build failed"])[0]
        super().__init__(message, report)
        self.diagnostics = diagnostics
        self.log = log_text


class Capabilities:
    """What the context offers, for the compatibility layer and the log.

    Attributes:
        gl_version: e.g. 450 (`ctx.version_code`).
        glsl_version: The highest GLSL version the driver compiles (desktop GL ≥ 3.3: the same number).
        has_fp64: Double-precision types are available (GL 4.0+, or `GL_ARB_gpu_shader_fp64`).
        renderer, vendor, version_string: The GL strings.
        max_texture_size: `GL_MAX_TEXTURE_SIZE`.
    """

    def __init__(self, ctx):
        self.gl_version = int(ctx.version_code)
        self.glsl_version = self.gl_version if self.gl_version >= 330 else 330
        self.has_fp64 = self.gl_version >= 400 or "GL_ARB_gpu_shader_fp64" in ctx.extensions
        self.renderer = ctx.info.get("GL_RENDERER", "OpenGL")
        self.vendor = ctx.info.get("GL_VENDOR", "")
        self.version_string = ctx.info.get("GL_VERSION", "")
        self.max_texture_size = int(ctx.info.get("GL_MAX_TEXTURE_SIZE", 4096))

    def describe(self) -> list[str]:
        return [f"Vendor: {self.vendor}", f"Renderer: {self.renderer}", f"GL Driver: {self.version_string}",
                f"Maximum texture size: {self.max_texture_size}x{self.max_texture_size}",
                f"GLSL up to {self.glsl_version}" + (" · double precision available" if self.has_fp64 else " · no double precision")]


class FragEngine:
    """Owns the context and the caches; creates jobs (see the module docstring).

    Args:
        ctx: An existing moderngl context to use (tests); a standalone one is created otherwise.
    """
    name = "Fragments GPU"

    def __init__(self, ctx=None):
        self.ctx = ctx if ctx is not None else create_context()
        self.owns_context = ctx is None
        self.capabilities = Capabilities(self.ctx)
        self.renderer = self.capabilities.renderer
        self.triangle = self.ctx.buffer(TRIANGLE.tobytes())
        self.surfaces = SurfaceCache(self.ctx)
        self._programs: dict[tuple[str, str], Program] = {}
        self.copy_program = Program(self.ctx, self.ctx.program(vertex_shader=COPY_VERTEX, fragment_shader=COPY_FRAGMENT), self.triangle)
        self.textures = TextureCache(self.ctx)

    # --- programs ------------------------------------------------------------------------------------------------------
    def build(self, modern: ModernSource) -> tuple[Program, bool]:
        """`(program, from_cache)` for translated sources; raises `FragBuildError` when the driver rejects them."""
        key = (modern.vertex, modern.fragment)
        cached = self._programs.get(key)
        if cached is not None:
            self._programs[key] = self._programs.pop(key)
            return cached, True
        started = time.perf_counter()
        try:
            program = self.ctx.program(vertex_shader=modern.vertex, fragment_shader=modern.fragment)
        except Exception as exc:  # noqa: BLE001 - moderngl.Error carries the compiler log
            log_text = str(exc)
            diagnostics = parse_log(log_text, modern.vertex_map, modern.fragment_map, modern.vertex, modern.fragment)
            report = write_failure_report({"vertex shader": modern.vertex, "fragment shader": modern.fragment}, log_text, self.renderer)
            raise FragBuildError(diagnostics, log_text, report) from exc
        wrapped = Program(self.ctx, program, self.triangle, (time.perf_counter() - started) * 1000.0)
        self._programs[key] = wrapped
        while len(self._programs) > PROGRAM_CACHE_LIMIT:
            self._programs.pop(next(iter(self._programs))).release()
        return wrapped, False

    def check(self, modern: ModernSource) -> list[Diagnostic]:
        """Compile without keeping the result; the diagnostics (empty when it compiled) — *Test GLSL versions*."""
        try:
            program = self.ctx.program(vertex_shader=modern.vertex, fragment_shader=modern.fragment)
        except Exception as exc:  # noqa: BLE001
            return parse_log(str(exc), modern.vertex_map, modern.fragment_map, modern.vertex, modern.fragment)
        program.release()
        return []

    def bind_textures(self, program: Program, request) -> None:
        """Bind the request's textures to units 1…; unit 0 stays the back / front buffer."""
        self.textures.bind(program, request)

    # --- the service protocol ---------------------------------------------------------------------------------------------
    def start(self, request, settings):
        """A new job (the service protocol): a render for a `FragRequest`, a chore for a `FragTask`."""
        from .job import FragJob
        from .tasks import FragTask, FragTaskJob
        if isinstance(request, FragTask):
            return FragTaskJob(self, request, settings)
        return FragJob(self, request, settings)

    def close(self) -> None:
        """Release every GPU object (and the context when this engine created it)."""
        for program in self._programs.values():
            program.release()
        self._programs.clear()
        self.surfaces.release()
        self.textures.release()
        self.copy_program.release()
        self.triangle.release()
        if self.owns_context:
            self.ctx.release()


class FragEngineFactory:
    """Plugs `FragEngine` into a `RenderService` (no fallback: fragments need a GL context)."""

    def create(self) -> tuple[FragEngine, str]:
        engine = FragEngine()
        return engine, f"Fragments GPU ({engine.renderer})"

    def fallback(self, engine) -> None:
        return None


__all__ = ["FragEngine", "FragEngineFactory", "FragBuildError", "Capabilities"]
