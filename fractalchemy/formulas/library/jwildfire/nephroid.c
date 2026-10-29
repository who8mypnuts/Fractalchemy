/*
    Fractalchemy formula library — translated from the JWildfire variation
        NephroidFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double nephroid_r;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("nephroid");

APO_VARIABLES(
    VAR_REAL(nephroid_r, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double theta = atan2(FTy, FTx);
    FPx += VVAR * VAR(nephroid_r) * (2.0 * cos(theta) - cos(2.0 * theta));
    FPy += VVAR * VAR(nephroid_r) * (2.0 * sin(theta) - sin(2.0 * theta));
    
    return TRUE;
}
