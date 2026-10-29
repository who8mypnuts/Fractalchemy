"""Every variation is defined twice (numpy + GLSL); the two must agree.

Runs over the whole registry — the native builtins and every compiled formula — so adding a
formula file automatically adds its checks. The evaluation itself is `formulas/verify.py` (shared with the
Formula Editor's probe and *Check numpy vs GLSL*): both engines run the same points through the same
wrapper the render code generator uses (`t`/`tz` in, `v`/`vz`/`col` out).
"""

import math

import numpy as np
import pytest

from fractalchemy.formulas import verify
from fractalchemy.fractal import variations as V
from fractalchemy.render.gpu_engine import gpu_available

needs_gl = pytest.mark.skipif(not gpu_available()[0], reason=f"no OpenGL: {gpu_available()[1]}")

SAMPLE_POINTS = verify.SAMPLE_POINTS
COEFS = verify.COEFS
_params = verify.test_params
prepared_params = verify.prepared_params


def _run_numpy(var: V.Variation, params: dict[str, float]) -> np.ndarray:
    return verify.evaluate_numpy(var, params=params)


def _glsl_program(ctx, var: V.Variation, params: dict[str, float]):
    return verify.glsl_program(ctx, var, params)


def _run_glsl(ctx, program) -> np.ndarray:
    return verify.run_glsl(ctx, program)


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
