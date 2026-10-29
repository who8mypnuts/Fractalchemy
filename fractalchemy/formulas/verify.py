"""Run one variation on both engines outside a render: the point probe and the numpy-vs-GLSL check.

Both engines get the same points through the same wrapper the render code generator uses (`t` / `tz` in,
`v` / `vz` / `col` out), so a disagreement here is a disagreement in a render. `tests/test_variations.py`
runs `compare()` over the whole registry; the Formula Editor runs it on the formula being written.

    evaluate_numpy(var, points, params)            # (n, 7): t, v, colour after the variation
    evaluate_glsl(ctx, var, points, params)        # the same on an OpenGL context (moderngl)
    compare(var, ctx)                              # a VerifyReport
    probe(var, (x, y, z), ctx=None)                # one point on numpy (and GLSL when a context is given)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..fractal import variations as V
from ..render import codegen

COEFS = (0.8, 0.1, -0.2, 0.9, 0.3, -0.4)
SAMPLE_POINTS = np.array([
    [0.3, 0.4, 0.1], [-0.7, 0.2, -0.3], [0.5, -0.6, 0.2], [-0.25, -0.9, 0.0], [1.3, 0.1, 0.5], [0.05, 1.7, -0.1],
    [-1.1, -1.2, 0.3], [0.9, 0.9, -0.4], [0.0, 0.5, 0.2], [0.5, 0.0, -0.2], [2.0, -0.3, 0.1], [-0.1, 0.01, 0.0],
], dtype=np.float64)
ACCUMULATOR = (0.2, -0.1, 0.05)      # what post_ variations read
WEIGHT = 0.6
ATOL = RTOL = 3e-4
COLUMNS = ("FTx", "FTy", "FTz", "FPx", "FPy", "FPz", "TC")


def test_params(var: V.Variation) -> dict[str, float]:
    """Non-default parameter values so parameter plumbing is exercised (integers stay integral, ranges respected)."""
    out = {}
    for key, default in var.params.items():
        info = var.param_info.get(key)
        value = (default if default else 0.7) * 1.3
        if info is not None and info.type == "int":
            value = int(default) + 1 if default >= 0 else int(default) - 1
            if info.nonzero and value == 0:
                value = 1
        if info is not None:
            if info.min is not None:
                value = max(value, info.min)
            if info.max is not None:
                value = min(value, info.max)
        out[key] = value
    return out


def prepared_params(var: V.Variation, params: dict[str, float] | None = None, weight: float = WEIGHT, coefs=COEFS) -> dict[str, float]:
    """The full parameter set an engine sees: the given (or default) values plus prepared constants and tables."""
    full = {key: params.get(key, default) if params else default for key, default in var.params.items()}
    if var.prepare is not None:
        full.update(var.prepare(full, weight, tuple(coefs), np.random.default_rng(0)))
    full.update(var.tables)
    return full


def _inputs(points: np.ndarray, accumulator=ACCUMULATOR, colour: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    pts = np.asarray(points, dtype=np.float64).reshape(-1, 3)
    acc = np.tile(np.asarray(accumulator, dtype=np.float64), (len(pts), 1))
    col = np.linspace(0.1, 0.9, len(pts)) if colour is None else np.asarray(colour, dtype=np.float64)
    return pts, acc, col


def evaluate_numpy(var: V.Variation, points: np.ndarray = SAMPLE_POINTS, params: dict[str, float] | None = None,
                   weight: float = WEIGHT, coefs=COEFS) -> np.ndarray:
    """`points` (n, 3) through the variation on the CPU engine; returns (n, 7): t, v, colour after it.

    `params` are the user-facing values (missing ones take their defaults); prepared constants are derived here.
    """
    pts, acc, col = _inputs(points)
    full = prepared_params(var, params, weight, coefs)
    point = V.Point(pts[:, 0].copy(), pts[:, 1].copy(), weight, tuple(coefs), full, np.random.default_rng(0), pts[:, 2].copy(),
                    acc[:, 0].copy(), acc[:, 1].copy(), acc[:, 2].copy(), col.copy())
    with np.errstate(all="ignore"):
        state = var.apply(point)
    n = len(pts)
    return np.column_stack([np.broadcast_to(np.asarray(s, dtype=np.float64), n) for s in state])


def glsl_program(ctx, var: V.Variation, params: dict[str, float], weight: float = WEIGHT, coefs=COEFS):
    """The probe shader plus the parameter texture it reads through `P()`, exactly like the engine."""
    c = coefs
    flat: list[float] = []
    indices = {}
    for key, value in params.items():
        indices[key] = len(flat)
        flat.extend(float(v) for v in value) if isinstance(value, (list, tuple)) else flat.append(float(value))
    if var.style == V.FORMULA:
        decls = codegen.bind_params(var.glsl_decls.replace("@", "vf"), indices)
        body = codegen.bind_params(var.glsl.replace("@", "vf"), indices)
        function = f"{decls}\nvoid vf({codegen.VARIATION_SIGNATURE}) {{\n{body}\n}}\n"
        call = "vf(t, tz, v, vz, col, w, c00, c01, c10, c11, c20, c21, s);" + (codegen.z_pass_glsl(var.kind, "w") if var.z == V.Z_PASS else "")
    else:
        function = ""
        call = codegen.bind_params(var.glsl, indices) + (" vz += w * tz;" if var.z == V.Z_PASS else "")
    source = f"""
#version 330
#define EPS 1e-10
#define PI 3.14159265358979323846
uint rng(inout uint s) {{ s ^= s << 13u; s ^= s >> 17u; s ^= s << 5u; return s; }}
float rnd(inout uint s) {{ return float(rng(s) >> 8u) * (1.0 / 16777216.0); }}
uniform sampler2D u_params;
float P(int i) {{ return texelFetch(u_params, ivec2(i & 255, i >> 8), 0).r; }}
{codegen.GLSL_PRELUDE}
{function}
in vec3 in_t;
in vec3 in_v;
in float in_col;
out vec3 out_t;
out vec3 out_v;
out float out_col;
void main() {{
    uint s = uint(gl_VertexID) + 7u;
    vec2 t = in_t.xy; float tz = in_t.z;
    vec2 v = in_v.xy; float vz = in_v.z;
    float col = in_col;
    float w = {weight!r};
    float c00 = {c[0]!r}, c01 = {c[1]!r}, c10 = {c[2]!r}, c11 = {c[3]!r}, c20 = {c[4]!r}, c21 = {c[5]!r};
    float r2 = dot(t, t); float r = sqrt(r2);
    float theta = r2 > 0.0 ? atan(t.x, t.y) : 0.0; float phi = r2 > 0.0 ? atan(t.y, t.x) : 0.0;
    {{ {call} }}
    out_t = vec3(t, tz); out_v = vec3(v, vz);
    out_col = col + ((in_t.x > 1e30 || in_v.x > 1e30 || in_col > 1e30) ? 1.0 : 0.0);   // keeps every input attribute alive
}}
"""
    program = ctx.program(vertex_shader=source, varyings=["out_t", "out_v", "out_col"])
    padded = np.zeros(max(256, len(flat) + (-len(flat) % 256)), dtype=np.float32)
    padded[:len(flat)] = flat
    texture = ctx.texture((256, len(padded) // 256), 1, padded.tobytes(), dtype="f4")
    texture.filter = (ctx.NEAREST, ctx.NEAREST)
    program._fractalchemy_params = texture   # kept alive with the program
    return program


def run_glsl(ctx, program, points: np.ndarray = SAMPLE_POINTS) -> np.ndarray:
    """Run a probe program over `points`; returns (n, 7) float64: t, v, colour after the variation."""
    import moderngl
    pts, acc, col = _inputs(points)
    n = len(pts)
    data = np.column_stack([pts, acc, col]).astype(np.float32)
    buf = ctx.buffer(data.tobytes())
    out = ctx.buffer(reserve=n * 7 * 4)
    vao = ctx.vertex_array(program, [(buf, "3f 3f 1f", "in_t", "in_v", "in_col")])
    texture = getattr(program, "_fractalchemy_params", None)
    if texture is not None:
        texture.use(0)
        if "u_params" in program:
            program["u_params"].value = 0
    vao.transform(out, mode=moderngl.POINTS)
    result = np.frombuffer(out.read(), dtype=np.float32).reshape(n, 7).astype(np.float64)
    for obj in (vao, buf, out):
        obj.release()
    return result


def evaluate_glsl(ctx, var: V.Variation, points: np.ndarray = SAMPLE_POINTS, params: dict[str, float] | None = None,
                  weight: float = WEIGHT, coefs=COEFS) -> np.ndarray:
    """`points` through the variation's GLSL on `ctx`; returns (n, 7) like `evaluate_numpy`."""
    full = prepared_params(var, params, weight, coefs)
    program = glsl_program(ctx, var, full, weight, coefs)
    try:
        return run_glsl(ctx, program, points)
    finally:
        program._fractalchemy_params.release()
        program.release()


@dataclass
class VerifyReport:
    """The outcome of `compare()`.

    Attributes:
        rows: How many points were compared.
        bad_rows: Points where numpy and GLSL disagree beyond the tolerance (random formulas: not compared).
        max_error: The largest absolute difference over the finite values.
        finite: Fraction of finite outputs on both engines.
        random: The formula uses random numbers, so only finiteness was checked.
        numpy_out, glsl_out: The (n, 7) results.
        message: One line for the status bar.
    """
    rows: int
    bad_rows: int
    max_error: float
    finite: float
    random: bool
    numpy_out: np.ndarray = field(repr=False)
    glsl_out: np.ndarray = field(repr=False)
    message: str = ""

    @property
    def ok(self) -> bool:
        """True when the engines agree (one point may differ: float32 on the other side of a discontinuity)."""
        return self.finite > 0.75 and self.bad_rows <= 1


def compare(var: V.Variation, ctx, points: np.ndarray = SAMPLE_POINTS, params: dict[str, float] | None = None) -> VerifyReport:
    """Evaluate on both engines and compare (`ATOL` / `RTOL`, scaled by the magnitude of the values)."""
    full = prepared_params(var, params or test_params(var))
    expected = evaluate_numpy(var, points, full)
    actual = evaluate_glsl(ctx, var, points, full)
    both_finite = np.isfinite(expected) & np.isfinite(actual)
    finite = float(both_finite.mean())
    if var.random:
        report = VerifyReport(len(points), 0, float("nan"), finite, True, expected, actual)
        report.message = f"random formula: GLSL compiles and {finite:.0%} of the outputs are finite"
        return report
    scale = np.maximum(1.0, np.abs(expected[both_finite])).max() if both_finite.any() else 1.0
    close = np.isclose(actual, expected, atol=ATOL * scale, rtol=RTOL) | ~both_finite
    bad_rows = int((~close.all(axis=1)).sum())
    diff = np.abs(actual - expected)[both_finite]
    max_error = float(diff.max()) if diff.size else 0.0
    report = VerifyReport(len(points), bad_rows, max_error, finite, False, expected, actual)
    report.message = (f"numpy and GLSL agree on {len(points) - bad_rows} of {len(points)} points (max difference {max_error:.2e})"
                      if report.ok else f"numpy and GLSL differ on {bad_rows} of {len(points)} points (max difference {max_error:.2e})")
    return report


@dataclass
class ProbeResult:
    """One point through the formula: the inputs and the outputs per engine (`glsl` None without a context)."""
    point: tuple[float, float, float]
    numpy: np.ndarray
    glsl: np.ndarray | None

    def lines(self) -> list[str]:
        """Readable rows: `FPx  numpy 0.123  glsl 0.123`."""
        out = []
        for i, name in enumerate(COLUMNS):
            row = f"{name:<4} numpy {self.numpy[i]: .6g}"
            if self.glsl is not None:
                row += f"   glsl {self.glsl[i]: .6g}"
            out.append(row)
        return out


def probe(var: V.Variation, point: tuple[float, float, float], params: dict[str, float] | None = None, ctx=None,
          weight: float = 1.0, coefs=(1.0, 0.0, 0.0, 1.0, 0.0, 0.0)) -> ProbeResult:
    """One point (FTx, FTy, FTz) through the formula: weight 1, the identity affine, the small fixed `ACCUMULATOR`
    (so post_ formulas have something to rewrite)."""
    pts = np.array([point], dtype=np.float64)
    full = prepared_params(var, params, weight, coefs)
    numpy_out = _probe_numpy(var, pts, full, weight, coefs)
    glsl_out = None
    if ctx is not None:
        program = glsl_program(ctx, var, full, weight, coefs)
        try:
            glsl_out = run_glsl(ctx, program, pts)[0]
        finally:
            program._fractalchemy_params.release()
            program.release()
    return ProbeResult(tuple(float(v) for v in point), numpy_out, glsl_out)


def _probe_numpy(var: V.Variation, pts: np.ndarray, params: dict[str, float], weight: float, coefs) -> np.ndarray:
    pts, acc, col = _inputs(pts)
    point = V.Point(pts[:, 0].copy(), pts[:, 1].copy(), weight, tuple(coefs), params, np.random.default_rng(0), pts[:, 2].copy(),
                    acc[:, 0].copy(), acc[:, 1].copy(), acc[:, 2].copy(), col.copy())
    with np.errstate(all="ignore"):
        state = var.apply(point)
    return np.array([float(np.asarray(s).reshape(-1)[0]) for s in state])


def create_context():
    """A standalone OpenGL context for `evaluate_glsl` / `compare` (raises when none can be made)."""
    from ..render.gpu_engine import create_context as make
    return make()


__all__ = ["SAMPLE_POINTS", "COEFS", "WEIGHT", "ACCUMULATOR", "COLUMNS", "test_params", "prepared_params", "evaluate_numpy",
           "glsl_program", "run_glsl", "evaluate_glsl", "VerifyReport", "compare", "ProbeResult", "probe", "create_context"]
