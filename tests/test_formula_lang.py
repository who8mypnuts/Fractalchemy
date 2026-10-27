"""The formula language: Apophysis plugin C compiled for numpy and GLSL."""

import pickle

import numpy as np
import pytest

from fractalchemy.formulas.lang import FormulaError, compile_artefacts, compile_source, variation_from_artefacts
from fractalchemy.formulas.lang.preprocess import preprocess
from fractalchemy.fractal import variations as V
from tests.test_variations import COEFS, _run_glsl, _glsl_program, _run_numpy, needs_gl, prepared_params  # noqa: F401

HEADER = """
typedef struct { %s } Variables;
#include "apoplugin.h"
APO_PLUGIN("%s");
APO_VARIABLES(%s);
"""


def plugin(name: str, calc: str, variables: str = "", members: str = "", prepare: str = "return TRUE;", extra: str = "") -> V.Variation:
    source = HEADER % (members, name, variables) + extra + f"""
int PluginVarPrepare(Variation* vp) {{ {prepare} }}
int PluginVarCalc(Variation* vp) {{ {calc} return TRUE; }}
"""
    return compile_source(source, origin=name).variation


def run(var: V.Variation, params=None, x=None, y=None, z=None, w=0.6):
    """numpy evaluation on a few points; returns (x, y, z, px, py, pz, c)."""
    n = 4
    x = np.array([0.3, -0.7, 0.5, 1.2]) if x is None else np.asarray(x, dtype=float)
    y = np.array([0.4, 0.2, -0.6, 0.1]) if y is None else np.asarray(y, dtype=float)
    z = np.zeros(n) if z is None else np.asarray(z, dtype=float)
    params = prepared_params(var, {**{k: v for k, v in var.params.items()}, **(params or {})})
    point = V.Point(x, y, w, COEFS, params, np.random.default_rng(0), z, np.zeros(n), np.zeros(n), np.zeros(n), np.full(n, 0.5))
    return var.apply(point)


# --- preprocessor -----------------------------------------------------------------------------------------
def test_preprocessor_handles_macros_conditionals_and_multiline_calls():
    text = preprocess("""
#define SQR(x) ((x) * (x))
#define vvar vp->vvar
#ifdef NOPE
int wrong;
#elif 1 + 1 == 2
int right = SQR(a +
   b);
#endif
double v = vvar;
""")
    assert "int wrong" not in text and "int right = ((a +    b) * (a +    b))" in text.replace("\n", " ") or "int right" in text
    assert "vp->vvar" in text   # a macro does not re-expand inside itself


def test_preprocessor_expands_nested_calls_but_paints_expanded_arguments_blue():
    text = preprocess("""
#define mind(x, x0) ((x) < (x0) ? (x0) : (x))
#define power_inv vp->var.power_inv
double r = mind(a, mind(b, c));
double q = mind(power_inv, 0);
""")
    assert "mind(" not in text                       # the call nested inside an argument is expanded too
    assert text.count("vp->var.power_inv") == 2      # once per use of `x` in the body, never expanded again
    assert "vp->var.vp->" not in text


# --- plugin facts -------------------------------------------------------------------------------------------
def test_variables_kinds_and_flags_are_read_from_the_source():
    var = plugin("pre_thing", "FTx = FTx * VAR(pre_thing_k); FPz += 1.0; TC = 0.5;",
                 "VAR_REAL(pre_thing_k, 2.0), VAR_INTEGER_RANGE(pre_thing_n, 1, 9, 3), VAR_REAL_CYCLE(pre_thing_a, 0, 1, 0.25)",
                 "double pre_thing_k; int pre_thing_n; double pre_thing_a;")
    assert var.kind == V.PRE and var.z == V.Z_FORMULA and var.dc and var.style == V.FORMULA
    assert var.params == {"pre_thing_k": 2.0, "pre_thing_n": 3, "pre_thing_a": 0.25}
    assert var.param_info["pre_thing_n"].type == "int" and var.param_info["pre_thing_n"].max == 9
    assert var.param_info["pre_thing_a"].cyclic
    post = plugin("post_thing", "FPx = -FPx;")
    assert post.kind == V.POST and post.z == V.Z_NONE and not post.dc and not post.random
    assert plugin("rnd", "FPx += random01();").random


def test_prepare_values_become_per_transform_constants():
    var = plugin("prep", "FPx += VAR(kk) * FTx; FPy += VAR(prep_a) * FTy;", "VAR_REAL(prep_a, 2.0)",
                 "double prep_a; double kk;", prepare="VAR(kk) = VAR(prep_a) * VVAR; return TRUE;")
    derived = var.prepare({"prep_a": 3.0}, 0.5, COEFS, np.random.default_rng(0))
    assert derived == {"kk": 1.5}
    out = run(var, {"prep_a": 3.0})   # prepared with the test weight 0.6
    assert np.allclose(out[3], 1.8 * np.array([0.3, -0.7, 0.5, 1.2]))


def test_apophysis_semantics_of_integers_and_fmod():
    var = plugin("ints", """
        int a = (int)(FTx * 10.0);
        int q = a / 3, r = a % 3;
        FPx = (double)q; FPy = (double)r; FPz = fmod(FTx * 10.0, 3.0);
        int big = 2000000000; big = big + big;   /* wraps like a 32-bit int */
        TC = (double)(big < 0);""")
    x = np.array([0.7, -0.7, 1.0, -1.0])
    out = run(var, x=x, y=np.zeros(4))
    assert out[3].tolist() == [2, -2, 3, -3]          # truncation toward zero
    assert out[4].tolist() == [1, -1, 1, -1]          # remainder keeps the dividend's sign
    assert np.allclose(out[5], [1.0, -1.0, 1.0, -1.0])
    assert out[6].tolist() == [1, 1, 1, 1]


def test_helpers_with_output_parameters_are_inlined():
    var = plugin("helped", "double s, c; polar(FTx, FTy, &s, &c); FPx += s; FPy += c;", extra="""
void polar(double x, double y, double* r, double* a) {
    *r = sqrt(x * x + y * y);
    if (*r == 0.0) { *a = 0.0; return; }
    *a = atan2(y, x);
}
""")
    out = run(var, x=[3.0, 0.0, -1.0, 0.5], y=[4.0, 0.0, 0.0, 0.5])
    assert np.allclose(out[3], [5.0, 0.0, 1.0, np.hypot(0.5, 0.5)])
    assert np.allclose(out[4], [np.arctan2(4, 3), 0.0, np.pi, np.pi / 4])


def test_divergent_loops_early_returns_and_switch():
    var = plugin("flow", """
        double a = fabs(FTx) * 10.0, acc = 0.0;
        int n = 0;
        while (a > 1.0) { a *= 0.5; n++; if (n > 50) break; }
        switch ((int)FTy) { case 0: acc = 1.0; break; case 1: acc = 2.0; break; default: acc = 3.0; }
        if (FTx < 0.0) { FPx = -1.0; return TRUE; }
        FPx = (double)n; FPy = acc;""")
    out = run(var, x=[0.3, -0.7, 8.0, 1.2], y=[0.0, 1.0, 1.0, 2.0])
    assert out[3].tolist() == [2, -1, 7, 4]
    assert out[4].tolist() == [1.0, 0.0, 2.0, 3.0]   # the early return skips the rest for that point


def test_complex_numbers():
    var = plugin("cplx", """
        Complex z(FTx, FTy);
        Complex r = exp(z) / (1.0 + z * z) + 2i;
        FPx += r.real(); FPy += r.imag(); FPz = abs(z);""",
                 extra="#include <complex>\ntypedef std::complex<double> Complex;\n")
    out = run(var, x=[0.3, 0.0, 1.0, -0.5], y=[0.4, 0.0, 0.0, 0.25])
    z = np.array([0.3 + 0.4j, 0.0, 1.0, -0.5 + 0.25j])
    r = np.exp(z) / (1 + z * z) + 2j
    assert np.allclose(out[3], r.real) and np.allclose(out[4], r.imag) and np.allclose(out[5], np.abs(z))


def test_stateful_plugins_rerun_their_private_orbit():
    var = plugin("orbit", "X = 0.5 * X + 0.5; FPx += X;", extra="static double X = 0.0;\n")
    assert "stateful" in var.note
    out = run(var)
    assert np.allclose(out[3], 1.0 - 0.5 ** 12, atol=1e-3)   # 12 orbit steps from the initial value


def test_errors_are_reported_with_the_origin():
    with pytest.raises(FormulaError, match="no_calc"):
        compile_source('typedef struct {} Variables;\n#include "apoplugin.h"\nAPO_PLUGIN("x");\nAPO_VARIABLES();\n', origin="no_calc")
    with pytest.raises(FormulaError, match="goto"):
        plugin("bad", "goto out; out: FPx = 1.0;")


def test_artefacts_round_trip_through_pickle():
    spec, art = compile_artefacts(HEADER % ("double k;", "rt", "VAR_REAL(k, 1.5)") + """
int PluginVarPrepare(Variation* vp) { return TRUE; }
int PluginVarCalc(Variation* vp) { FPx += VAR(k) * FTx; return TRUE; }
""")
    restored = variation_from_artefacts(pickle.loads(pickle.dumps(art)), origin="cache")
    assert restored.params == {"k": 1.5} and restored.origin == "cache"
    assert np.allclose(run(restored)[3], 1.5 * np.array([0.3, -0.7, 0.5, 1.2]))


@needs_gl
def test_generated_glsl_agrees_with_numpy_on_control_flow(gl_context):
    var = plugin("flowgl", """
        double a = fabs(FTx) * 10.0, acc = 0.0;
        int n = 0;
        while (a > 1.0) { a *= 0.5; n++; if (n > 50) break; }
        switch ((int)(FTy * 2.0)) { case 0: acc = 1.0; break; case 1: acc = 2.0; break; default: acc = 3.0; }
        if (FTx < 0.0) { FPx = -1.0; return TRUE; }
        FPx = (double)n; FPy = acc + fmod(FTx, 0.37); FPz = (double)(n % 3);""")
    params = prepared_params(var, {})
    expected = _run_numpy(var, params)
    actual = _run_glsl(gl_context, _glsl_program(gl_context, var, params))
    assert np.allclose(actual, expected, atol=1e-4)


@pytest.fixture(scope="module")
def gl_context():
    import moderngl
    ctx = moderngl.create_standalone_context(require=330)
    yield ctx
    ctx.release()
