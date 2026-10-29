/*
    Fractalchemy formula library — translated from the JWildfire variation
        OuroborosFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double ouroboros_radius;
    double ouroboros_twist;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("ouroboros");

APO_VARIABLES(
    VAR_REAL(ouroboros_radius, 0.5),
    VAR_REAL(ouroboros_twist, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double or_radius = max(fabs(VAR(ouroboros_radius)), 0.01);
    double or_r = sqrt(FTx * FTx + FTy * FTy);
    double or_theta = atan2(FTy, FTx);
    double or_wrapped_r = or_radius * ((or_r / or_radius) - floor(or_r / or_radius));
    double or_nt = or_theta + VAR(ouroboros_twist) * or_r;
    FPx += VVAR * or_wrapped_r * cos(or_nt);
    FPy += VVAR * or_wrapped_r * sin(or_nt);
    
    return TRUE;
}
