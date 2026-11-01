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
    """The display pass over `surface.front_texture` into `target_fbo`, then the request's colour grading if any."""
    ctx = engine.ctx
    if getattr(request, "debug_view", "") == "depth":
        engine.depth_view.apply(surface, target_fbo, width, height, *depth_range(surface))
        return
    grading = getattr(request, "grading", None)
    graded = grading is not None and not grading.is_identity
    if graded and buffer_program is None:
        engine.grading.apply(grading, surface.front_texture, target_fbo, width, height)      # straight from the accumulation
        return
    first_target = engine.grading.intermediate(width, height) if graded else target_fbo
    first_target.use()
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
    if graded:
        engine.grading.apply(grading, engine.grading.texture, target_fbo, width, height)


def depth_range(surface: Surface) -> tuple[float, float]:
    """`(near, far)` depth values of the hits in the front buffer, for a readable depth display (0, 1 when nothing hit)."""
    import numpy as np

    data = np.frombuffer(surface.front_fbo.read(components=1, attachment=-1, dtype="f4"), dtype=np.float32)
    hits = data[data < 1.0]
    if hits.size == 0:
        return 0.0, 1.0
    near, far = float(np.percentile(hits, 1)), float(np.percentile(hits, 99))
    return (near, far) if far > near else (near, near + 1e-6)


__all__ = ["draw_subframe", "display", "split_rects", "depth_range"]
