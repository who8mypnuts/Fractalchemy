/*
    Fractalchemy formula library — translated from the JWildfire variation
        AstroidFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double astroid_a;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("astroid");

APO_VARIABLES(
    VAR_REAL(astroid_a, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double theta = atan2(FTy, FTx);
    double ct = cos(theta);
    double st = sin(theta);
    FPx += VVAR * VAR(astroid_a) * ct * ct * ct;
    FPy += VVAR * VAR(astroid_a) * st * st * st;
    
    return TRUE;
}
