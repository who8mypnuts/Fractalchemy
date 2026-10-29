/*
    Fractalchemy formula library — translated from the JWildfire variation
        InvoluteFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double involute_r;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("involute");

APO_VARIABLES(
    VAR_REAL(involute_r, 0.3)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t = atan2(FTy, FTx);
    FPx += VVAR * VAR(involute_r) * (cos(t) + t * sin(t));
    FPy += VVAR * VAR(involute_r) * (sin(t) - t * cos(t));
    
    return TRUE;
}
