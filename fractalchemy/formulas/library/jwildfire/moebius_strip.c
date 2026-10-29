/*
    Fractalchemy formula library — translated from the JWildfire variation
        MoebiusStripFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double moebius_strip_radius;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("moebius_strip");

APO_VARIABLES(
    VAR_REAL(moebius_strip_radius, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double ms_rad = max(fabs(VAR(moebius_strip_radius)), 0.01);
    double ms_r = sqrt(FTx * FTx + FTy * FTy);
    double ms_theta = atan2(FTy, FTx);
    double ms_h = ms_r - ms_rad;
    double ms_twist = ms_theta * 0.5;
    double ms_new_h = ms_h * cos(ms_twist);
    double ms_new_r = ms_rad + ms_new_h;
    FPx += VVAR * ms_new_r * cos(ms_theta);
    FPy += VVAR * ms_new_r * sin(ms_theta);
    
    return TRUE;
}
