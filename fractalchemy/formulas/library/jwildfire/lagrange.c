/*
    Fractalchemy formula library — translated from the JWildfire variation
        LagrangeFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double lagrange_separation;
    double lagrange_strength;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("lagrange");

APO_VARIABLES(
    VAR_REAL(lagrange_separation, 0.5),
    VAR_REAL(lagrange_strength, 0.2)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double lg_sep = max(fabs(VAR(lagrange_separation)), 0.01);
    double lg_m1x = - lg_sep * 0.5;
    double lg_m2x = lg_sep * 0.5;
    double lg_dx1 = FTx - lg_m1x;
    double lg_dx2 = FTx - lg_m2x;
    double lg_r1 = sqrt(lg_dx1 * lg_dx1 + FTy * FTy) + 0.1;
    double lg_r2 = sqrt(lg_dx2 * lg_dx2 + FTy * FTy) + 0.1;
    double lg_px = - VAR(lagrange_strength) * (lg_dx1 / (lg_r1 * lg_r1 * lg_r1) + lg_dx2 / (lg_r2 * lg_r2 * lg_r2));
    double lg_py = - VAR(lagrange_strength) * (FTy / (lg_r1 * lg_r1 * lg_r1) + FTy / (lg_r2 * lg_r2 * lg_r2));
    FPx += VVAR * (FTx + lg_px);
    FPy += VVAR * (FTy + lg_py);
    
    return TRUE;
}
