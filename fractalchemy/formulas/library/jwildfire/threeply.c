/*
    Fractalchemy formula library — translated from the JWildfire variation
        ThreeplyFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

// keeps a private orbit between points (JWildfire fields updated per point): the statics below
typedef struct {
    double threeply_a;
    double threeply_b;
    double threeply_c;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("threeply");

APO_VARIABLES(
    VAR_REAL(threeply_a, -55),
    VAR_REAL(threeply_b, -1),
    VAR_REAL(threeply_c, -42)
);

static double x0 = 0;
static double y0 = 0;

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    int sgn = (x0 > 0) ? 1 : (x0 < 0) ? - 1 : 0;
    double xn = y0 - sgn * fabs(sin(x0) * cos(VAR(threeply_b)) + VAR(threeply_c) - x0 * sin(VAR(threeply_a) + VAR(threeply_b) + VAR(threeply_c)));
    double yn = VAR(threeply_a) - x0;
    FPx = 0.001 * xn * VVAR;
    FPy = 0.001 * yn * VVAR;
    x0 = xn;
    y0 = yn;
    
    return TRUE;
}
