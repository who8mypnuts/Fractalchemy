"""The GL side of colour grading: one program and an intermediate float target, applied after the display pass.

`GradingStage.apply` runs `grading.GRADING_FRAGMENT` over a texture into the caller's framebuffer. When the fragment
has a buffer shader the display pass draws into the stage's own RGBA16F texture first (`intermediate`), so the
grading sees the tone-mapped image; without one it samples the accumulation directly.
"""

from __future__ import annotations

from ..grading import GRADING_FRAGMENT, Grading
from .program import Program


class GradingStage:
    """Owns the grading program and a lazily sized intermediate target."""

    def __init__(self, ctx, triangle, copy_vertex: str):
        self.ctx = ctx
        self.program = Program(ctx, ctx.program(vertex_shader=copy_vertex, fragment_shader=GRADING_FRAGMENT), triangle)
        self._texture = None
        self._fbo = None
        self._size: tuple[int, int] | None = None

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
        target_fbo.use()
        self.ctx.viewport = (0, 0, width, height)
        source_texture.use(0)
        self.program.set("frontbuffer", 0)
        for name, value in grading.uniforms().items():
            self.program.set(name, value)
        self.program.render()

    @property
    def texture(self):
        return self._texture

    def release_target(self) -> None:
        for obj in (self._fbo, self._texture):
            if obj is not None:
                obj.release()
        self._fbo = self._texture = None
        self._size = None

    def release(self) -> None:
        self.release_target()
        self.program.release()


__all__ = ["GradingStage"]
