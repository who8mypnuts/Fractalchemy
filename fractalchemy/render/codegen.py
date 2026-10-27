"""Generate the GPU preview's GLSL for one flame.

The *structure* of a flame (which xforms exist, which variations each uses) is
baked into the shader; every *number* (affine coefficients, weights, parameters,
xaos table, opacities) lives in a float texture read through `P(index)`. Changing
a slider therefore only re-uploads the texture; adding a variation recompiles.

Two vertex shaders are produced:

* **iterate** — advances each point one (or `u_iters`) chaos-game steps and writes the
  new state back through transform feedback;
* **plot** — applies the final xform, projects through the camera and emits the
  palette colour for additive blending into the histogram.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..fractal.variations import pre_blur_glsl
from .compiled import CompiledFlame, CompiledXForm

PARAMS_WIDTH = 256   # float texture width; index -> (i % 256, i / 256)

_PRELUDE = """
#version 330
#define EPS 1e-10
#define PI 3.14159265358979323846
uniform sampler2D u_params;
float P(int i) { return texelFetch(u_params, ivec2(i & 255, i >> 8), 0).r; }
uint rng(inout uint s) { s ^= s << 13u; s ^= s >> 17u; s ^= s << 5u; return s; }
float rnd(inout uint s) { return float(rng(s) >> 8u) * (1.0 / 16777216.0); }
uint hash(uint x) { x ^= x >> 16u; x *= 0x7feb352du; x ^= x >> 15u; x *= 0x846ca68bu; x ^= x >> 16u; return x == 0u ? 1u : x; }
"""


@dataclass
class GeneratedProgram:
    """Shader sources plus the matching parameter block."""
    iterate_vertex: str
    plot_vertex: str
    params: np.ndarray          # float32, length multiple of PARAMS_WIDTH
    xform_count: int

    @property
    def params_texture_size(self) -> tuple[int, int]:
        """(width, height) of the float texture holding `params`."""
        return PARAMS_WIDTH, len(self.params) // PARAMS_WIDTH


class _Params:
    """Appends floats and hands back their indices."""
    def __init__(self):
        self.values: list[float] = []

    def add(self, value: float) -> int:
        """Append one value; returns its index."""
        self.values.append(float(value))
        return len(self.values) - 1

    def block(self, values) -> int:
        """Append several values; returns the index of the first."""
        start = len(self.values)
        self.values.extend(float(v) for v in values)
        return start

    def array(self) -> np.ndarray:
        """The values as float32, zero-padded to whole texture rows."""
        padded = len(self.values) + (-len(self.values) % PARAMS_WIDTH) or PARAMS_WIDTH
        out = np.zeros(padded, dtype=np.float32)
        out[:len(self.values)] = self.values
        return out


def generate(compiled: CompiledFlame) -> GeneratedProgram:
    """Shaders and parameter block for `compiled`."""
    params = _Params()
    n = compiled.count
    functions = [_xform_function(f"xf_{i}", x, params) for i, x in enumerate(compiled.xforms)]
    chaos_base = params.block(compiled.selection.reshape(-1))
    opacity_base = params.block([x.opacity for x in compiled.xforms])
    final_fn = _xform_function("xf_final", compiled.final, params) if compiled.final is not None else ""

    cases = "\n".join(f"            case {i}: xf_{i}(p, c, s); break;" for i in range(n))
    iterate = f"""{_PRELUDE}
uniform int u_iters;
in vec4 in_state;
in uint in_seed;
out vec4 out_state;
out uint out_seed;
{''.join(functions)}
int select_xform(int prev, float r) {{
    int base = {chaos_base} + prev * {n};
    for (int j = 0; j < {n - 1}; j++) {{ if (r < P(base + j)) return j; }}
    return {n - 1};
}}
void main() {{
    uint s = in_seed;
    vec2 p = in_state.xy;
    float c = in_state.z;
    int xi = int(in_state.w);
    for (int k = 0; k < u_iters; k++) {{
        xi = select_xform(xi, rnd(s));
        switch (xi) {{
{cases}
        }}
        if (!(abs(p.x) < 1e10 && abs(p.y) < 1e10)) {{ p = vec2(rnd(s), rnd(s)) * 2.0 - 1.0; c = rnd(s); }}
    }}
    out_state = vec4(p, c, float(xi));
    out_seed = s;
}}
"""
    final_call = "    xf_final(p, c, s);\n" if final_fn else ""
    plot = f"""{_PRELUDE}
uniform sampler2D u_palette;
uniform vec3 u_cam_x;   // clip x = dot(u_cam_x, vec3(p, 1))
uniform vec3 u_cam_y;
uniform uint u_salt;
in vec4 in_state;
out vec4 v_color;
{final_fn}
void main() {{
    vec2 p = in_state.xy;
    float c = in_state.z;
    int xi = int(in_state.w);
    uint s = hash(uint(gl_VertexID) ^ u_salt);
{final_call}    float op = P({opacity_base} + xi);
    vec3 h = vec3(p, 1.0);
    vec2 clip = vec2(dot(u_cam_x, h), dot(u_cam_y, h));
    bool ok = abs(p.x) < 1e10 && abs(p.y) < 1e10 && op > 0.0;
    gl_Position = ok ? vec4(clip, 0.0, 1.0) : vec4(2.0, 2.0, 0.0, 1.0);
    gl_PointSize = 1.0;
    int ci = int(clamp(c, 0.0, 1.0) * 255.0 + 0.5);
    v_color = vec4(texelFetch(u_palette, ivec2(ci, 0), 0).rgb * op, op);
}}
"""
    return GeneratedProgram(iterate, plot, params.array(), n)


def _xform_function(name: str, xform: CompiledXForm, params: _Params) -> str:
    coefs = params.block(xform.coefs)
    post = params.block(xform.post)
    color = params.add(xform.color)
    speed = params.add(xform.color_speed)
    pre_blur = params.add(xform.pre_blur)
    lines = [
        f"void {name}(inout vec2 p, inout float c, inout uint s) {{",
        "    float c00 = P(%d), c01 = P(%d), c10 = P(%d), c11 = P(%d), c20 = P(%d), c21 = P(%d);" % tuple(coefs + i for i in range(6)),
        "    vec2 t = vec2(c00 * p.x + c10 * p.y + c20, c01 * p.x + c11 * p.y + c21);",
    ]
    if xform.pre_blur:
        lines.append(f"    {{ float pb = P({pre_blur}); {pre_blur_glsl()} }}")
    lines += [
        "    float r2 = dot(t, t); float r = sqrt(r2);",
        "    float theta = r2 > 0.0 ? atan(t.x, t.y) : 0.0; float phi = r2 > 0.0 ? atan(t.y, t.x) : 0.0;",
        "    vec2 v = vec2(0.0);",
    ]
    for cv in xform.variations:
        weight = params.add(cv.weight)
        body = cv.variation.glsl
        for key, value in cv.params.items():
            body = body.replace(f"P_{key}", f"P({params.add(value)})")
        lines.append(f"    {{ float w = P({weight}); {body} }}   // {cv.variation.name}")
    if xform.has_post:
        lines.append("    float p00 = P(%d), p01 = P(%d), p10 = P(%d), p11 = P(%d), p20 = P(%d), p21 = P(%d);" % tuple(post + i for i in range(6)))
        lines.append("    p = vec2(p00 * v.x + p10 * v.y + p20, p01 * v.x + p11 * v.y + p21);")
    else:
        lines.append("    p = v;")
    lines.append(f"    c = c * (1.0 - P({speed})) + P({color}) * P({speed});")
    lines.append("}\n")
    return "\n".join(lines)
