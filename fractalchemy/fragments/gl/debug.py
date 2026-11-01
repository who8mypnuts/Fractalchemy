"""Debug displays of the accumulation: the depth buffer as a picture (the raytracers write `gl_FragDepth`).

`DEPTH_FRAGMENT` samples the surface's depth texture and shows near as bright, far as dark, with the background
(depth 1.0) black and a few iso-depth lines so the shape of the estimator's hits can be read at a glance.
"""

from __future__ import annotations

from .program import Program

DEPTH_FRAGMENT = """#version 330 core
in vec2 v_uv;
uniform sampler2D depthbuffer;
uniform float u_near;
uniform float u_far;
out vec4 fragColor;
void main() {
    float d = texture(depthbuffer, v_uv).r;
    if (d >= 1.0) { fragColor = vec4(0.0, 0.0, 0.0, 1.0); return; }
    float t = clamp((d - u_near) / max(u_far - u_near, 1e-6), 0.0, 1.0);
    float shade = 1.0 - t;
    float line = step(0.47, abs(fract(t * 16.0) - 0.5));
    vec3 c = mix(vec3(shade), vec3(0.2, 0.6, 1.0), line * 0.6);
    fragColor = vec4(c, 1.0);
}
"""


class DepthView:
    """The depth display program (`engine.depth_view`)."""

    def __init__(self, ctx, triangle, copy_vertex: str):
        self.ctx = ctx
        self.program = Program(ctx, ctx.program(vertex_shader=copy_vertex, fragment_shader=DEPTH_FRAGMENT), triangle)

    def apply(self, surface, target_fbo, width: int, height: int, near: float = 0.0, far: float = 1.0) -> None:
        """Draw the front buffer's depth into `target_fbo`, stretched between `near` and `far` depth values."""
        target_fbo.use()
        self.ctx.viewport = (0, 0, width, height)
        surface.front_depth.use(0)
        self.program.set("depthbuffer", 0)
        self.program.set("u_near", float(near))
        self.program.set("u_far", float(far))
        self.program.render()

    def release(self) -> None:
        self.program.release()


__all__ = ["DepthView", "DEPTH_FRAGMENT"]
