/*
    Fractalchemy formula library — translated from the JWildfire variation
        EpitrochoidFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double epitrochoid_r_big;
    double epitrochoid_r_small;
    double epitrochoid_d;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("epitrochoid");

APO_VARIABLES(
    VAR_REAL(epitrochoid_r_big, 3),
    VAR_REAL(epitrochoid_r_small, 1),
    VAR_REAL(epitrochoid_d, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double ep_r = max(fabs(VAR(epitrochoid_r_small)), 1e-4);
    double theta = atan2(FTy, FTx);
    double ratio = (VAR(epitrochoid_r_big) + ep_r) / ep_r;
    FPx += VVAR * ((VAR(epitrochoid_r_big) + ep_r) * cos(theta) - VAR(epitrochoid_d) * cos(ratio * theta));
    FPy += VVAR * ((VAR(epitrochoid_r_big) + ep_r) * sin(theta) - VAR(epitrochoid_d) * sin(ratio * theta));
    
    return TRUE;
}
