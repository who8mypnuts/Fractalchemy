"""Every variation is defined twice (numpy + GLSL); the two must agree.

Runs over the whole registry — the native builtins and every compiled formula — so adding a
formula file automatically adds its checks. Both engines run the same points through the
same wrapper the render code generator uses (`t`/`tz` in, `v`/`vz`/`col` out).
"""

import math

import numpy as np
import pytest

from fractalchemy.fractal import variations as V
from fractalchemy.render import codegen
from fractalchemy.render.gpu_engine import gpu_available

needs_gl = pytest.mark.skipif(not gpu_available()[0], reason=f"no OpenGL: {gpu_available()[1]}")

COEFS = (0.8, 0.1, -0.2, 0.9, 0.3, -0.4)
SAMPLE_POINTS = np.array([
    [0.3, 0.4, 0.1], [-0.7, 0.2, -0.3], [0.5, -0.6, 0.2], [-0.25, -0.9, 0.0], [1.3, 0.1, 0.5], [0.05, 1.7, -0.1],
    [-1.1, -1.2, 0.3], [0.9, 0.9, -0.4], [0.0, 0.5, 0.2], [0.5, 0.0, -0.2], [2.0, -0.3, 0.1], [-0.1, 0.01, 0.0],
], dtype=np.float64)
ACCUMULATOR = np.array([[0.2, -0.1, 0.05]] * len(SAMPLE_POINTS))   # post_ variations read this
COLOUR = np.linspace(0.1, 0.9, len(SAMPLE_POINTS))
WEIGHT = 0.6


def _params(var: V.Variation) -> dict[str, float]:
    """Non-default parameter values so parameter plumbing is exercised (integers stay integral)."""
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


def prepared_params(var: V.Variation, params: dict[str, float]) -> dict[str, float]:
    params = dict(params)
    if var.prepare is not None:
        params.update(var.prepare(params, WEIGHT, COEFS, np.random.default_rng(0)))
    params.update(var.tables)
    return params


def _glsl_program(ctx, var: V.Variation, params: dict[str, float]):
    """The test shader plus the parameter texture it reads through `P()`, exactly like the engine."""
    c = COEFS
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
    float w = {WEIGHT!r};
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


def _run_glsl(ctx, program) -> np.ndarray:
    """Returns (n, 7) float64: t, v, colour after the variation."""
    import moderngl
    n = len(SAMPLE_POINTS)
    data = np.column_stack([SAMPLE_POINTS, ACCUMULATOR, COLOUR]).astype(np.float32)
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


def _run_numpy(var: V.Variation, params: dict[str, float]) -> np.ndarray:
    rng = np.random.default_rng(0)
    pts, acc = SAMPLE_POINTS, ACCUMULATOR
    point = V.Point(pts[:, 0].copy(), pts[:, 1].copy(), WEIGHT, COEFS, params, rng, pts[:, 2].copy(),
                    acc[:, 0].copy(), acc[:, 1].copy(), acc[:, 2].copy(), COLOUR.copy())
    with np.errstate(all="ignore"):
        state = var.apply(point)
    n = len(pts)
    return np.column_stack([np.broadcast_to(np.asarray(s, dtype=np.float64), n) for s in state])


ALL = sorted(V.REGISTRY)
DETERMINISTIC = sorted(v.name for v in V.REGISTRY.values() if not v.random and (v.glsl or v.style == V.FORMULA))
RANDOM = sorted(v.name for v in V.REGISTRY.values() if v.random and (v.glsl or v.style == V.FORMULA))


def test_registry_has_the_flam3_classics_and_aliases():
    for name in ("linear", "spherical", "swirl", "julian", "bubble", "elliptic", "mobius", "lazysusan"):
        assert name in V.REGISTRY
    assert V.resolve("linear3D") is V.REGISTRY["linear"]
    assert V.resolve("nonexistent_variation") is None
    assert V.REGISTRY["julian"].param_keys() == ["julian_power", "julian_dist"]
    assert V.parameter_owner("julian_power") == "julian"


def test_normalize_resolves_aliases_renames_params_and_reports_unknowns():
    variations, params, unsupported = V.normalize(
        {"linear3D": 0.5, "linear": 0.25, "mystery": 0.3, "zero": 0.0},
        {"mystery_a": 1.0})
    assert variations == {"linear": 0.75}
    assert unsupported == ["mystery"]
    assert "mystery_a" not in params


def test_kinds_and_depth_flags_follow_apophysis():
    assert V.REGISTRY["pre_blur"].kind == V.PRE and V.REGISTRY["flatten"].kind == V.POST
    assert V.REGISTRY["spherical"].z == V.Z_PASS and V.REGISTRY["bubble"].z == V.Z_FORMULA
    assert V.REGISTRY["zscale"].z == V.Z_FORMULA


@pytest.mark.parametrize("name", ALL)
def test_numpy_implementation_is_finite_on_ordinary_points(name):
    var = V.REGISTRY[name]
    out = _run_numpy(var, prepared_params(var, _params(var)))
    assert out.shape == (len(SAMPLE_POINTS), 7)
    if name in V.REGISTRY and not var.note.startswith("may"):
        finite = np.isfinite(out)
        assert finite.mean() > 0.75, f"{name}: {out}"   # a few singular points are fine, garbage is not


@needs_gl
@pytest.mark.parametrize("name", DETERMINISTIC)
def test_glsl_matches_numpy(name, gl_context):
    var = V.REGISTRY[name]
    params = prepared_params(var, _params(var))
    expected = _run_numpy(var, params)
    actual = _run_glsl(gl_context, _glsl_program(gl_context, var, params))
    both_finite = np.isfinite(expected) & np.isfinite(actual)
    assert both_finite.mean() > 0.75, f"{name}: numpy {expected}\nglsl {actual}"
    scale = np.maximum(1.0, np.abs(expected[both_finite]))
    close = np.isclose(actual, expected, atol=3e-4 * scale.max(), rtol=3e-4) | ~both_finite
    bad_rows = int((~close.all(axis=1)).sum())
    # One point may legitimately differ: float32 lands on the other side of a discontinuity, or an
    # ill-conditioned step (acosh near 1, sin(x)*43758 hashes) loses its digits on the GPU.
    assert bad_rows <= 1, f"{name}: {bad_rows} points differ\nglsl {actual}\nnumpy {expected}"


@needs_gl
@pytest.mark.parametrize("name", RANDOM)
def test_random_glsl_compiles_and_is_finite(name, gl_context):
    var = V.REGISTRY[name]
    params = prepared_params(var, _params(var))
    out = _run_glsl(gl_context, _glsl_program(gl_context, var, params))
    assert np.isfinite(out).mean() > 0.75, f"{name}: {out}"


def test_pre_blur_jitter_is_centred():
    var = V.REGISTRY["pre_blur"]
    rng = np.random.default_rng(1)
    n = 20000
    point = V.Point(np.zeros(n), np.zeros(n), 0.5, COEFS, {}, rng)
    dx, dy = var.numpy(point)
    assert abs(dx.mean()) < 0.01 and abs(dy.mean()) < 0.01
    assert 0.1 < math.hypot(dx.std(), dy.std()) < 0.6


@pytest.fixture(scope="module")
def gl_context():
    import moderngl
    try:
        ctx = moderngl.create_standalone_context(require=330)
    except Exception:  # noqa: BLE001
        ctx = moderngl.create_standalone_context(require=330, backend="egl")
    yield ctx
    ctx.release()
