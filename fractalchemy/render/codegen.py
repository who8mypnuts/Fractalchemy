"""Generate the GPU preview's GLSL for one flame.

The *structure* of a flame (which xforms exist, which variations each uses) is
baked into the shader; every *number* (affine coefficients, weights, parameters,
xaos table, opacities) lives in a float texture read through `P(index)`. Changing
a slider therefore only re-uploads the texture; adding a variation recompiles.

Two vertex shaders are produced:

* **iterate** — advances each point one (or `u_iters`) chaos-game steps and writes the
  new state back through transform feedback;
* **plot** — applies the final xform, projects through the 3D and 2D cameras and emits
  the palette colour for additive blending into the histogram.

Per point the state is `(x, y, z, colour)` plus the index of the last xform and an RNG seed.
Formula-style variations (compiled from the plugin dialect) become one GLSL function per
use; legacy snippets are inlined. Within an xform the order is Apophysis's: `pre_`
variations, then the precalculated angles/lengths, then the rest, then `post_` ones.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

from ..formulas.lang import GLSL_PRELUDE
from ..fractal.variations import FORMULA, POST, PRE, Z_PASS, pre_blur_glsl
from .compiled import CompiledFlame, CompiledVariation, CompiledXForm
from .projection import GLSL_PROJECT

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
""" + GLSL_PRELUDE

VARIATION_SIGNATURE = ("inout vec2 t, inout float tz, inout vec2 v, inout float vz, inout float col, float w, "
                       "float c00, float c01, float c10, float c11, float c20, float c21, inout uint s")
STATE_FLOATS = 4     # x, y, z, colour
STATE_BYTES = (STATE_FLOATS + 2) * 4


@dataclass
class GeneratedProgram:
    """Shader sources plus the matching parameter block."""
    iterate_vertex: str
    plot_vertex: str
    params: np.ndarray          # float32, length multiple of PARAMS_WIDTH
    xform_count: int

    @property
    def params_texture_size(self) -> tuple[int, int]:
        return PARAMS_WIDTH, len(self.params) // PARAMS_WIDTH


class _Params:
    """Appends floats and hands back their indices."""
    def __init__(self):
        self.values: list[float] = []

    def add(self, value: float) -> int:
        self.values.append(float(value))
        return len(self.values) - 1

    def block(self, values) -> int:
        start = len(self.values)
        self.values.extend(float(v) for v in values)
        return start

    def array(self) -> np.ndarray:
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
in uint in_xi;
in uint in_seed;
out vec4 out_state;
out uint out_xi;
out uint out_seed;
{''.join(functions)}
int select_xform(int prev, float r) {{
    int base = {chaos_base} + prev * {n};
    for (int j = 0; j < {n - 1}; j++) {{ if (r < P(base + j)) return j; }}
    return {n - 1};
}}
void main() {{
    uint s = in_seed;
    vec3 p = in_state.xyz;
    float c = in_state.w;
    int xi = int(in_xi);
    for (int k = 0; k < u_iters; k++) {{
        xi = select_xform(xi, rnd(s));
        switch (xi) {{
{cases}
        }}
        if (!(abs(p.x) < 1e10 && abs(p.y) < 1e10 && abs(p.z) < 1e10)) {{ p = vec3(rnd(s) * 2.0 - 1.0, rnd(s) * 2.0 - 1.0, 0.0); c = rnd(s); }}
    }}
    out_state = vec4(p, c);
    out_xi = uint(xi);
    out_seed = s;
}}
"""
    final_call = "    xf_final(p, c, s);\n" if final_fn else ""
    plot = f"""{_PRELUDE}
uniform sampler2D u_palette;
uniform vec3 u_cam_x;   // clip x = dot(u_cam_x, vec3(q, 1))
uniform vec3 u_cam_y;
uniform uint u_salt;
{GLSL_PROJECT}
in vec4 in_state;
in uint in_xi;
out vec4 v_color;
{final_fn}
void main() {{
    vec3 p = in_state.xyz;
    float c = in_state.w;
    int xi = int(in_xi);
    uint s = hash(uint(gl_VertexID) ^ u_salt);
{final_call}    float op = P({opacity_base} + xi);
    vec2 q = project3d(p, s);
    vec3 h = vec3(q, 1.0);
    vec2 clip = vec2(dot(u_cam_x, h), dot(u_cam_y, h));
    bool ok = abs(q.x) < 1e10 && abs(q.y) < 1e10 && op > 0.0;
    gl_Position = ok ? vec4(clip, 0.0, 1.0) : vec4(2.0, 2.0, 0.0, 1.0);
    gl_PointSize = 1.0;
    int ci = int(clamp(c, 0.0, 1.0) * 255.0 + 0.5);
    v_color = vec4(texelFetch(u_palette, ivec2(ci, 0), 0).rgb * op, op);
}}
"""
    return GeneratedProgram(iterate, plot, params.array(), n)


def bind_params(text: str, values: dict[str, int]) -> str:
    """Replace `P_<name>` placeholders by `P(index)` reads and `PA_<name>(i)` table reads by `P(base + i)`
    (whole names only, so `P_x` leaves `P_xx` alone)."""
    for key, index in sorted(values.items(), key=lambda kv: -len(kv[0])):
        text = re.sub(r"\bPA_" + re.escape(key) + r"\(", f"P({index} + ", text)
        text = re.sub(r"\bP_" + re.escape(key) + r"\b", f"P({index})", text)
    return text


def _variation_code(tag: str, cv: CompiledVariation, params: _Params) -> tuple[str, str]:
    """(declarations before the xform function, statement inside it) for one variation use."""
    weight = params.add(cv.weight)
    indices = {key: (params.block(value) if isinstance(value, (list, tuple)) else params.add(value)) for key, value in cv.params.items()}
    var = cv.variation
    if var.style == FORMULA:
        decls = bind_params(var.glsl_decls.replace("@", tag), indices)
        body = bind_params(var.glsl.replace("@", tag), indices)
        function = f"{decls}\nvoid {tag}({VARIATION_SIGNATURE}) {{\n{body}\n}}\n"
        call = f"    {tag}(t, tz, v, vz, col, P({weight}), c00, c01, c10, c11, c20, c21, s);   // {var.name}"
        if var.z == Z_PASS:
            call += z_pass_glsl(var.kind, f"P({weight})")
        return function, call
    body = bind_params(var.glsl, indices)
    if var.z == Z_PASS:
        body += " vz += w * tz;"
    return "", f"    {{ float w = P({weight}); {body} }}   // {var.name}"


def z_pass_glsl(kind: str, weight: str) -> str:
    """Apophysis's depth rule for a formula-style variation that does not set the depth itself."""
    if kind == PRE:
        return f" tz *= {weight};"
    if kind == POST:
        return f" vz *= {weight};"
    return f" vz += {weight} * tz;"


def _xform_function(name: str, xform: CompiledXForm, params: _Params) -> str:
    coefs = params.block(xform.coefs)
    post = params.block(xform.post)
    color = params.add(xform.color)
    speed = params.add(xform.color_speed)
    var_color = params.add(xform.var_color)
    pre_blur = params.add(xform.pre_blur)
    decls: list[str] = []
    calls: dict[str, list[str]] = {PRE: [], "normal": [], POST: []}
    for k, cv in enumerate(xform.variations):
        d, call = _variation_code(f"{name}_v{k}", cv, params)
        if d:
            decls.append(d)
        calls[cv.variation.kind if cv.variation.kind in (PRE, POST) else "normal"].append(call)
    lines = [
        f"void {name}(inout vec3 p, inout float c, inout uint s) {{",
        "    float c00 = P(%d), c01 = P(%d), c10 = P(%d), c11 = P(%d), c20 = P(%d), c21 = P(%d);" % tuple(coefs + i for i in range(6)),
        f"    c = c * (1.0 - P({speed})) + P({color}) * P({speed});",
        "    float col = c;",
        "    vec2 t = vec2(c00 * p.x + c10 * p.y + c20, c01 * p.x + c11 * p.y + c21);",
        "    float tz = p.z;",
    ]
    if xform.pre_blur:
        lines.append(f"    {{ float pb = P({pre_blur}); {pre_blur_glsl()} }}")
    lines += ["    vec2 v = vec2(0.0); float vz = 0.0;"]
    lines += calls[PRE]
    lines += [
        "    float r2 = dot(t, t); float r = sqrt(r2);",
        "    float theta = r2 > 0.0 ? atan(t.x, t.y) : 0.0; float phi = r2 > 0.0 ? atan(t.y, t.x) : 0.0;",
    ]
    lines += calls["normal"]
    lines += calls[POST]
    if xform.has_post:
        lines.append("    float p00 = P(%d), p01 = P(%d), p10 = P(%d), p11 = P(%d), p20 = P(%d), p21 = P(%d);" % tuple(post + i for i in range(6)))
        lines.append("    p = vec3(p00 * v.x + p10 * v.y + p20, p01 * v.x + p11 * v.y + p21, vz);")
    else:
        lines.append("    p = vec3(v, vz);")
    if xform.direct_color:
        lines.append(f"    c = c + P({var_color}) * (col - c);")
    lines.append("}\n")
    return "\n".join(decls) + "\n" + "\n".join(lines)
