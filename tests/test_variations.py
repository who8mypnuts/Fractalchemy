"""Every variation is defined twice (numpy + GLSL); the two must agree."""

import math

import numpy as np
import pytest

from fractalchemy.fractal import variations as V
from fractalchemy.render.gpu_engine import gpu_available

needs_gl = pytest.mark.skipif(not gpu_available()[0], reason=f"no OpenGL: {gpu_available()[1]}")

COEFS = (0.8, 0.1, -0.2, 0.9, 0.3, -0.4)
SAMPLE_POINTS = np.array([
    [0.3, 0.4], [-0.7, 0.2], [0.5, -0.6], [-0.25, -0.9], [1.3, 0.1], [0.05, 1.7], [-1.1, -1.2], [0.9, 0.9],
    [0.0, 0.5], [0.5, 0.0], [2.0, -0.3], [-0.1, 0.01],
], dtype=np.float64)


def _params(var: V.Variation) -> dict[str, float]:
    """Non-default parameter values so parameter plumbing is exercised."""
    return {f"{var.name}_{p}": (default if default else 0.7) * 1.3 for p, default in var.params.items()}


def _glsl_program(ctx, var: V.Variation, weight: float, params: dict[str, float]):
    body = var.glsl
    for key, value in params.items():
        body = body.replace(f"P_{key}", f"({value!r})")
    c = COEFS
    source = f"""
#version 330
#define EPS 1e-10
#define PI 3.14159265358979323846
uint rng(inout uint s) {{ s ^= s << 13u; s ^= s >> 17u; s ^= s << 5u; return s; }}
float rnd(inout uint s) {{ return float(rng(s) >> 8u) * (1.0 / 16777216.0); }}
in vec2 in_t;
out vec2 out_v;
void main() {{
    uint s = uint(gl_VertexID) + 7u + (in_t.x > 1e30 ? 1u : 0u);   // keeps in_t alive for variations that ignore t
    vec2 t = in_t;
    float w = {weight!r};
    float c00 = {c[0]!r}, c01 = {c[1]!r}, c10 = {c[2]!r}, c11 = {c[3]!r}, c20 = {c[4]!r}, c21 = {c[5]!r};
    float r2 = dot(t, t); float r = sqrt(r2);
    float theta = r2 > 0.0 ? atan(t.x, t.y) : 0.0; float phi = r2 > 0.0 ? atan(t.y, t.x) : 0.0;
    vec2 v = vec2(0.0);
    {{ {body} }}
    out_v = v;
}}
"""
    return ctx.program(vertex_shader=source, varyings=["out_v"])


def _run_glsl(ctx, program, points: np.ndarray) -> np.ndarray:
    import moderngl
    buf = ctx.buffer(points.astype(np.float32).tobytes())
    out = ctx.buffer(reserve=buf.size)
    vao = ctx.vertex_array(program, [(buf, "2f", "in_t")])
    vao.transform(out, mode=moderngl.POINTS)
    result = np.frombuffer(out.read(), dtype=np.float32).reshape(-1, 2).astype(np.float64)
    for obj in (vao, buf, out):
        obj.release()
    return result


def _run_numpy(var: V.Variation, weight: float, params: dict[str, float], points: np.ndarray) -> np.ndarray:
    rng = np.random.default_rng(0)
    point = V.Point(points[:, 0].copy(), points[:, 1].copy(), weight, COEFS, params, rng)
    dx, dy = var.numpy(point)
    return np.column_stack([np.broadcast_to(dx, points.shape[0]), np.broadcast_to(dy, points.shape[0])])


DETERMINISTIC = sorted(v.name for v in V.REGISTRY.values() if not v.random and v.glsl)
RANDOM = sorted(v.name for v in V.REGISTRY.values() if v.random and v.glsl)


def test_registry_has_the_flam3_classics_and_aliases():
    for name in ("linear", "spherical", "swirl", "julian", "bubble", "elliptic", "mobius", "lazysusan"):
        assert name in V.REGISTRY
    assert V.resolve("linear3D") is V.REGISTRY["linear"]
    assert V.resolve("nonexistent_variation") is None
    assert V.REGISTRY["julian"].param_keys() == ["julian_power", "julian_dist"]


def test_normalize_resolves_aliases_renames_params_and_reports_unknowns():
    variations, params, unsupported = V.normalize(
        {"linear3D": 0.5, "linear": 0.25, "curl3D": 1.0, "mystery": 0.3, "zero": 0.0},
        {"curl3D_cx": 0.1, "curl3D_cy": 0.2, "mystery_a": 1.0})
    assert variations == {"linear": 0.75, "curl": 1.0}
    assert params["curl_cx"] == 0.1 and params["curl_cy"] == 0.2 and "curl3D_cx" not in params
    assert unsupported == ["mystery"]


@pytest.mark.parametrize("name", DETERMINISTIC)
def test_numpy_implementation_is_finite(name):
    var = V.REGISTRY[name]
    out = _run_numpy(var, 0.6, _params(var), SAMPLE_POINTS)
    assert out.shape == SAMPLE_POINTS.shape and np.isfinite(out).all()


@needs_gl
@pytest.mark.parametrize("name", DETERMINISTIC)
def test_glsl_matches_numpy(name, gl_context):
    var = V.REGISTRY[name]
    params = _params(var)
    expected = _run_numpy(var, 0.6, params, SAMPLE_POINTS)
    actual = _run_glsl(gl_context, _glsl_program(gl_context, var, 0.6, params), SAMPLE_POINTS)
    scale = np.maximum(1.0, np.abs(expected))
    assert np.allclose(actual, expected, atol=2e-4 * scale.max(), rtol=2e-4), f"{name}: {actual} vs {expected}"


@needs_gl
@pytest.mark.parametrize("name", RANDOM)
def test_random_glsl_compiles_and_is_finite(name, gl_context):
    var = V.REGISTRY[name]
    out = _run_glsl(gl_context, _glsl_program(gl_context, var, 0.6, _params(var)), SAMPLE_POINTS)
    assert np.isfinite(out).all()


def test_pre_blur_jitter_is_centred():
    var = V.REGISTRY["pre_blur"]
    rng = np.random.default_rng(1)
    n = 20000
    point = V.Point(np.zeros(n), np.zeros(n), 0.5, COEFS, {}, rng)
    dx, dy = var.numpy(point)
    assert abs(dx.mean()) < 0.01 and abs(dy.mean()) < 0.01
    assert 0.1 < math.hypot(dx.std(), dy.std()) < 0.6
