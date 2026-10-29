/*
    Fractalchemy formula library — translated from the JWildfire variation
        Ennepers2Func.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double ennepers2_a;
    double ennepers2_b;
    double ennepers2_c;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("ennepers2");

APO_VARIABLES(
    VAR_REAL(ennepers2_a, 1),
    VAR_REAL(ennepers2_b, 0.3333),
    VAR_REAL(ennepers2_c, 0.075)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double xx = FTx;
    double yy = FTy;
    double r2 = 1.0 / (sqr(xx) + sqr(yy));
    double dxy = (sqr(VAR(ennepers2_a) * xx) - sqr(VAR(ennepers2_b) * yy));
    FPx += VVAR * xx * (sqr(VAR(ennepers2_a)) - dxy * r2 - VAR(ennepers2_c) * sqrt(fabs(xx)));
    FPy += VVAR * yy * (sqr(VAR(ennepers2_b)) - dxy * r2 - VAR(ennepers2_c) * sqrt(fabs(yy)));
    FPz += VVAR * dxy * 0.5 * sqrt(r2);
    return TRUE;
}
