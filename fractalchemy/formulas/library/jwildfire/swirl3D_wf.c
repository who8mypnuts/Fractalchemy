/*
    Fractalchemy formula library — translated from the JWildfire variation
        Swirl3DWFFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double swirl3D_wf_n;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("swirl3D_wf");

APO_VARIABLES(
    VAR_REAL(swirl3D_wf_n, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double rad = (sqrt(FTx * FTx + FTy * FTy) + EPS);
    double ang = atan2(FTy, FTx);
    FPx += VVAR * (rad * cos(ang));
    FPy += VVAR * (rad * sin(ang));
    FPz += VVAR * (sin(6.0 * cos(rad) - VAR(swirl3D_wf_n) * ang));
    TC = fabs(sin(6.0 * cos(rad) - VAR(swirl3D_wf_n) * ang));
    return TRUE;
}
