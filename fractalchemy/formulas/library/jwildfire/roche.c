/*
    Fractalchemy formula library — translated from the JWildfire variation
        RocheFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double roche_sep;
    double roche_mass;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("roche");

APO_VARIABLES(
    VAR_REAL(roche_sep, 0.5),
    VAR_REAL(roche_mass, 0.5)
);

double clamp(double value, double min, double max)
{
    return max(min, min(max, value));
}

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double ro_sep = max(fabs(VAR(roche_sep)), 0.01);
    double ro_mass = clamp(VAR(roche_mass), 0.01, 0.99);
    double ro_mx = ro_sep * 0.5;
    double ro_dx1 = FTx - ro_mx;
    double ro_dx2 = FTx + ro_mx;
    double ro_r1 = max(sqrt(ro_dx1 * ro_dx1 + FTy * FTy), 0.01);
    double ro_r2 = max(sqrt(ro_dx2 * ro_dx2 + FTy * FTy), 0.01);
    double ro_r1_3 = ro_r1 * ro_r1 * ro_r1;
    double ro_r2_3 = ro_r2 * ro_r2 * ro_r2;
    double ro_px = - ro_mass * ro_dx1 / ro_r1_3 - (1.0 - ro_mass) * ro_dx2 / ro_r2_3;
    double ro_py = - ro_mass * FTy / ro_r1_3 - (1.0 - ro_mass) * FTy / ro_r2_3;
    FPx += VVAR * (FTx - ro_py * 0.5);
    FPy += VVAR * (FTy + ro_px * 0.5);
    
    return TRUE;
}
