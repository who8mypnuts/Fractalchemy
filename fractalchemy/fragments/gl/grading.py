"""The GL side of colour grading: the grading program, the bloom passes, the LUT texture and an intermediate target.

`GradingStage.apply` runs `grading.GRADING_FRAGMENT` over a texture into the caller's framebuffer. When the fragment
has a buffer shader the display pass draws into the stage's own RGBA16F texture first (`intermediate`), so the
grading sees the tone-mapped image; without one it samples the accumulation directly. Bloom is a bright pass and a
separable Gaussian blur at half resolution into two small textures the main pass adds back; a `.cube` LUT becomes
a 3D texture cached by path and modification time (a missing or malformed file is noted and skipped).
"""

from __future__ import annotations

from pathlib import Path

from ..grading import BLUR_FRAGMENT, BRIGHT_FRAGMENT, GRADING_FRAGMENT, Grading
from ..lut import LutError, read_cube
from .program import Program


class GradingStage:
    """Owns the grading programs, the bloom and LUT textures and a lazily sized intermediate target."""

    def __init__(self, ctx, triangle, copy_vertex: str):
        self.ctx = ctx
        self.program = Program(ctx, ctx.program(vertex_shader=copy_vertex, fragment_shader=GRADING_FRAGMENT), triangle)
        self.bright = Program(ctx, ctx.program(vertex_shader=copy_vertex, fragment_shader=BRIGHT_FRAGMENT), triangle)
        self.blur = Program(ctx, ctx.program(vertex_shader=copy_vertex, fragment_shader=BLUR_FRAGMENT), triangle)
        self._texture = None
        self._fbo = None
        self._size: tuple[int, int] | None = None
        self._bloom: list = []                  # two (texture, fbo) pairs at half resolution
        self._bloom_size: tuple[int, int] | None = None
        self._lut = None                        # (key, texture)
        self._fallback = ctx.texture((1, 1), 4, dtype="f2")
        self._fallback_lut = ctx.texture3d((1, 1, 1), 3, dtype="f4")
        self.notes: list[str] = []              # problems with the LUT file, for the log
        self._reported: set[str] = set()

    def intermediate(self, width: int, height: int):
        """An RGBA16F framebuffer of `width × height` for the pass whose output the grading reads."""
        if self._size != (width, height):
            self.release_target()
            self._texture = self.ctx.texture((width, height), 4, dtype="f2")
            self._fbo = self.ctx.framebuffer([self._texture])
            self._size = (width, height)
        return self._fbo

    def apply(self, grading: Grading, source_texture, target_fbo, width: int, height: int) -> None:
        """Grade `source_texture` into `target_fbo`."""
        bloom_texture = self._bloom_pass(grading, source_texture, width, height) if grading.has_bloom else self._fallback
        lut_texture, lut_size = self._lut_texture(grading) if grading.has_lut else (self._fallback_lut, 1)
        target_fbo.use()
        self.ctx.viewport = (0, 0, width, height)
        source_texture.use(0)
        bloom_texture.use(1)
        lut_texture.use(2)
        self.program.set("frontbuffer", 0)
        self.program.set("bloomTex", 1)
        self.program.set("lutTex", 2)
        self.program.set("u_lut_size", float(lut_size))
        for name, value in grading.uniforms().items():
            if name == "u_lut_strength" and lut_size <= 1:
                value = 0.0
            self.program.set(name, value)
        self.program.render()

    # --- bloom -----------------------------------------------------------------------------------------------------------
    def _bloom_targets(self, width: int, height: int) -> list:
        size = (max(1, width // 2), max(1, height // 2))
        if self._bloom_size != size:
            self._release_bloom()
            for _ in range(2):
                texture = self.ctx.texture(size, 4, dtype="f2")
                texture.repeat_x = texture.repeat_y = False
                self._bloom.append((texture, self.ctx.framebuffer([texture])))
            self._bloom_size = size
        return self._bloom

    def _bloom_pass(self, grading: Grading, source_texture, width: int, height: int):
        (tex_a, fbo_a), (tex_b, fbo_b) = self._bloom_targets(width, height)
        w, h = self._bloom_size
        self.ctx.viewport = (0, 0, w, h)
        fbo_a.use()
        source_texture.use(0)
        self.bright.set("frontbuffer", 0)
        self.bright.set("u_threshold", float(grading.bloom_threshold))
        self.bright.render()
        radius = max(1.0, float(grading.bloom_radius) / 2.0)              # half resolution: half the radius
        for source, fbo, step in ((tex_a, fbo_b, (1.0 / w, 0.0)), (tex_b, fbo_a, (0.0, 1.0 / h))):
            fbo.use()
            source.use(0)
            self.blur.set("frontbuffer", 0)
            self.blur.set("u_step", step)
            self.blur.set("u_radius", radius)
            self.blur.render()
        return tex_a

    # --- LUT --------------------------------------------------------------------------------------------------------------
    def _lut_texture(self, grading: Grading):
        path = Path(grading.lut)
        try:
            key = (str(path), path.stat().st_mtime_ns)
        except OSError:
            self._note(f"LUT not found: {path}")
            return self._fallback_lut, 1
        if self._lut is not None and self._lut[0] == key:
            return self._lut[1], self._lut[2]
        try:
            lut = read_cube(path)
        except (OSError, LutError) as exc:
            self._note(f"LUT {path.name} not used: {exc}")
            return self._fallback_lut, 1
        if self._lut is not None:
            self._lut[1].release()
        texture = self.ctx.texture3d((lut.size, lut.size, lut.size), 3, lut.bytes, dtype="f4")
        texture.repeat_x = texture.repeat_y = texture.repeat_z = False
        self._lut = (key, texture, lut.size)
        self._reported = set()
        return texture, lut.size

    def _note(self, text: str) -> None:
        if text not in self.notes and text not in self._reported:
            self.notes.append(text)

    def take_notes(self) -> list[str]:
        """The LUT problems found since the last call (each reported once)."""
        notes, self.notes = self.notes, []
        self._reported.update(notes)
        return notes

    @property
    def texture(self):
        return self._texture

    def release_target(self) -> None:
        for obj in (self._fbo, self._texture):
            if obj is not None:
                obj.release()
        self._fbo = self._texture = None
        self._size = None

    def _release_bloom(self) -> None:
        for texture, fbo in self._bloom:
            fbo.release()
            texture.release()
        self._bloom = []
        self._bloom_size = None

    def release(self) -> None:
        self.release_target()
        self._release_bloom()
        if self._lut is not None:
            self._lut[1].release()
            self._lut = None
        self._fallback.release()
        self._fallback_lut.release()
        for program in (self.program, self.bright, self.blur):
            program.release()


__all__ = ["GradingStage"]
