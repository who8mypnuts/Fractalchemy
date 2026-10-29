"""The JWildfire importer's translator: Java variation classes become dialect formulas that compile and verify."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from fractalchemy.formulas import verify  # noqa: E402
from fractalchemy.formulas.lang import compile_source  # noqa: E402
from fractalchemy.fractal import variations as V  # noqa: E402
from jwf_translate import Unsupported, find_author, translate  # noqa: E402

JAVA = '''
/*
  JWildfire - an image and animation processor written in Java
  Copyright (C) 1995-2021 Andreas Maschke
*/
package org.jwildfire.create.tina.variation;

import static org.jwildfire.base.mathlib.MathLib.*;

public class TwirlyFunc extends VariationFunc implements SupportsGPU {
  private static final long serialVersionUID = 1L;
  // Autor: Jane Example
  private static final String PARAM_POWER = "power";
  private static final String PARAM_TURNS = "turns";
  private static final String[] paramNames = {PARAM_POWER, PARAM_TURNS};
  private static final double SQRT3 = 1.7320508;
  private static final int offsets[][] = {{0, 1}, {1, 0}};

  private double power = 2.0;
  private int turns = 3;
  private double scale, half;
  private DoubleWrapperWF sina = new DoubleWrapperWF();
  private DoubleWrapperWF cosa = new DoubleWrapperWF();

  @Override
  public void transform(FlameTransformationContext pContext, XForm pXForm, XYZPoint pAffineTP, XYZPoint pVarTP, double pAmount) {
    double r = pAffineTP.getPrecalcSqrt();
    double a = pAffineTP.getPrecalcAtanYX() * this.turns + SQRT3 * 0.0;
    sinAndCos(a, sina, cosa);
    double k = pAmount * pow(r, this.scale) * Math.abs(this.half) + offsets[1][0] * 0.0;
    double[] buf = new double[2];
    buf[0] = k * cosa.value;
    buf[1] = k * sina.value;
    pVarTP.x += buf[0] + helper(r, pContext);
    pVarTP.y += buf[1];
    if (pContext.isPreserveZCoordinate()) {
      pVarTP.z += pAmount * pAffineTP.z;
    }
  }

  private double helper(double r, FlameTransformationContext pContext) {
    return r * 0.0;
  }

  @Override
  public String[] getParameterNames() {
    return paramNames;
  }

  @Override
  public Object[] getParameterValues() {
    return new Object[]{power, turns};
  }

  @Override
  public void setParameter(String pName, double pValue) {
    if (PARAM_POWER.equalsIgnoreCase(pName))
      power = pValue;
    else if (PARAM_TURNS.equalsIgnoreCase(pName))
      turns = Tools.FTOI(pValue);
    else
      throw new IllegalArgumentException(pName);
  }

  @Override
  public void init(FlameTransformationContext pContext, Layer pLayer, XForm pXForm, double pAmount) {
    this.scale = power * 0.5;
    this.half = pAmount / 2.0;
  }

  @Override
  public String getName() {
    return "twirly";
  }

  @Override
  public VariationFuncType[] getVariationTypes() {
    return new VariationFuncType[]{VariationFuncType.VARTYPE_2D, VariationFuncType.VARTYPE_SUPPORTS_GPU};
  }

  @Override
  public String getGPUCode(FlameTransformationContext context) {
    // based on code from the cudaLibrary.xml compilation, created by Steven Brodhead Sr.
    return "";
  }
}
'''


def test_translator_turns_a_variation_class_into_a_verified_formula():
    translation = translate(JAVA, "TwirlyFunc.java")
    assert translation.name == "twirly" and translation.author == "Jane Example"
    assert translation.params == [("twirly_power", 2.0, "real"), ("twirly_turns", 3.0, "int")]
    assert translation.derived == ["twirly_scale", "twirly_half"]
    source = translation.source
    assert 'APO_PLUGIN("twirly")' in source and "VAR_INTEGER(twirly_turns, 3)" in source and "#define SQRT3" in source
    assert "static const int offsets[][] = {" in source and "fsincos(a, & sina, & cosa)" in source and "double buf[2];" in source
    assert "FALSE" not in source and "FPz" not in source           # the preserve-z block is gone, so the formula stays 2D
    assert "double helper(double r)" in source and "helper(r)" in source   # the context argument dropped on both sides
    assert "VAR(twirly_scale) = VAR(twirly_power) * 0.5;" in source and "this." not in source
    compiled = compile_source(source)
    var = compiled.variation
    assert var.params == {"twirly_power": 2.0, "twirly_turns": 3} and var.z == V.Z_NONE and not var.random
    assert var.param_info["twirly_turns"].type == "int"
    out = verify.evaluate_numpy(var)
    assert out.shape[1] == 7 and abs(out).max() < 1e6
    try:
        ctx = verify.create_context()
    except Exception:  # noqa: BLE001
        pytest.skip("no OpenGL context")
    try:
        assert verify.compare(var, ctx).ok
    finally:
        ctx.release()


def test_translator_refuses_what_the_dialect_cannot_express():
    with pytest.raises(Unsupported, match="complex"):
        translate(JAVA.replace("double r = pAffineTP.getPrecalcSqrt();", "Complex z = new Complex(pAffineTP.x, pAffineTP.y); double r = 1.0;"))
    # a field updated per point is a private orbit: a `static` the compiler re-runs (JWildfire's attractor variations)
    stateful = translate(JAVA.replace("pVarTP.y += buf[1];", "pVarTP.y += buf[1]; half = r;"))
    assert "static double half = 0;" in stateful.source and "VAR(twirly_half)" not in stateful.source
    assert compile_source(stateful.source).variation.note.startswith("stateful plugin")
    # a seeded java.util.Random becomes the seeded 31-bit generator once per transform, true randomness per point
    random = translate(JAVA.replace("private double scale, half;", "private double scale, half; private Random rnd = new Random((long) power);")
                       .replace("this.half = pAmount / 2.0;", "this.half = pAmount / 2.0 + rnd.nextDouble();")
                       .replace("double[] buf = new double[2];", "double[] buf = new double[2]; double jitter = rnd.nextDouble();"))
    assert "int rnd = jw_seed((int) VAR(twirly_power));" in random.source and "jw_rand01(&rnd)" in random.source
    assert "double jitter = random01();" in random.source and compile_source(random.source).variation.random
    with pytest.raises(Unsupported, match="rewrites its parameters"):
        translate(JAVA.replace("pVarTP.y += buf[1];", "pVarTP.y += buf[1]; power = r;"))
    with pytest.raises(Unsupported, match="getName"):
        translate(JAVA.replace('return "twirly";', "return NAME;"))
    assert find_author("// Author: Jesus Sosa\n") == "Jesus Sosa" and find_author("created by Steven Brodhead Sr") == ""


def test_the_imported_library_is_loaded_and_verified():
    jwildfire = ROOT / "fractalchemy" / "formulas" / "library" / "jwildfire"
    files = sorted(jwildfire.glob("*.c"))
    assert len(files) >= 200
    for name in ("twintrian", "disc2", "flower", "parabola", "lissajous", "vogel", "hexagonal", "honeycomb", "ikeda", "clifford_js",
                 "lorenz_js", "bubble_wf", "tangent3D", "mercator", "epitrochoid", "symmetric_icon", "cos2_bs"):
        assert name in V.REGISTRY, name
        assert "jwildfire" in Path(V.REGISTRY[name].origin).parts, name
    for path in files:
        head = path.read_text(encoding="utf-8")[:600]
        assert "translated from the JWildfire variation" in head and "Lesser General Public License" in head, path
