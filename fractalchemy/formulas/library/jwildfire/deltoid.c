/*
    Fractalchemy formula library — translated from the JWildfire variation
        DeltoidFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double deltoid_r;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("deltoid");

APO_VARIABLES(
    VAR_REAL(deltoid_r, 0.33)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double theta = atan2(FTy, FTx);
    FPx += VVAR * (2.0 * VAR(deltoid_r) * cos(theta) + VAR(deltoid_r) * cos(2.0 * theta));
    FPy += VVAR * (2.0 * VAR(deltoid_r) * sin(theta) - VAR(deltoid_r) * sin(2.0 * theta));
    
    return TRUE;
}
