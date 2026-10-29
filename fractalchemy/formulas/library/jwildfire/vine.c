/*
    Fractalchemy formula library — translated from the JWildfire variation
        VineFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double vine_density;
    double vine_scale;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("vine");

APO_VARIABLES(
    VAR_REAL(vine_density, 1),
    VAR_REAL(vine_scale, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double vn_density = max(fabs(VAR(vine_density)), 0.01);
    double vn_scale = max(fabs(VAR(vine_scale)), 0.01);
    double vn_r = sqrt(FTx * FTx + FTy * FTy);
    double vn_theta = atan2(FTy, FTx);
    double vn_n = vn_r * vn_density;
    double vn_spiral = vn_theta + vn_n * 2.39996323;
    double vn_new_r = sqrt(vn_n) * vn_scale;
    FPx += VVAR * vn_new_r * cos(vn_spiral);
    FPy += VVAR * vn_new_r * sin(vn_spiral);
    
    return TRUE;
}
