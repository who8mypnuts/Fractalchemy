"""The two GL passes every fragment render is made of, shared by the viewport job and the hi-res renderer.

`draw_subframe` is FragM's `drawFragmentProgram`: the back buffer bound as `backbuffer`, the special uniforms
set, the user values uploaded, the fullscreen triangle drawn into the front buffer with the depth test always
passing (the raytracers write `gl_FragDepth` themselves). `display` is the second half of `drawToFrameBufferObject`:
the buffer shader (tone mapping) over the front buffer as `frontbuffer` — or a plain clamped copy when the fragment
has none — into whatever framebuffer the caller wants (RGBA8 for the screen, float for a hi-res image).
"""

from __future__ import annotations

from .program import Program
from .surfaces import Surface
from .uniforms import IDENTITY, set_special, upload_values


def draw_subframe(engine, program: Program, surface: Surface, request, time: float, projection: tuple[float, ...] = IDENTITY,
                  splits: int = 1) -> None:
    """One subframe into `surface` (swaps first; `surface.subframe` counts it).

    `splits` > 1 draws the subframe as `splits × splits` scissored rectangles — the same picture, in draws short
    enough not to trip the GPU watchdog (§6.8 of the plan).
    """
    ctx = engine.ctx
    surface.swap()
    surface.subframe += 1
    surface.front_fbo.use()
    ctx.viewport = (0, 0, surface.width, surface.height)
    surface.back_texture.use(0)
    engine.bind_textures(program, request)
    set_special(program, surface.width, surface.height, surface.subframe, time, projection)
    upload_values(program, request.values)
    ctx.enable(ctx.DEPTH_TEST)
    ctx.depth_func = "1"          # GL_ALWAYS
    if splits <= 1:
        program.render()
    else:
        for rect in split_rects(surface.width, surface.height, splits):
            surface.front_fbo.scissor = rect
            program.render()
        surface.front_fbo.scissor = None
    ctx.disable(ctx.DEPTH_TEST)


def split_rects(width: int, height: int, splits: int) -> list[tuple[int, int, int, int]]:
    """The `splits × splits` scissor rectangles `(x, y, w, h)` covering `width × height` exactly."""
    xs = [round(i * width / splits) for i in range(splits + 1)]
    ys = [round(j * height / splits) for j in range(splits + 1)]
    return [(xs[i], ys[j], xs[i + 1] - xs[i], ys[j + 1] - ys[j]) for j in range(splits) for i in range(splits)
            if xs[i + 1] > xs[i] and ys[j + 1] > ys[j]]


def display(engine, buffer_program: Program | None, surface: Surface, request, target_fbo, width: int, height: int, time: float) -> None:
    """The display pass over `surface.front_texture` into `target_fbo`."""
    ctx = engine.ctx
    target_fbo.use()
    ctx.viewport = (0, 0, width, height)
    surface.front_texture.use(0)
    if buffer_program is not None:
        set_special(buffer_program, surface.width, surface.height, surface.subframe, time, IDENTITY)
        upload_values(buffer_program, request.values)
        engine.bind_textures(buffer_program, request)
        buffer_program.render()
    else:
        engine.copy_program.set("frontbuffer", 0)
        engine.copy_program.render()


__all__ = ["draw_subframe", "display", "split_rects"]
