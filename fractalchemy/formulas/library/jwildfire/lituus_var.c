/*
    Fractalchemy formula library — translated from the JWildfire variation
        LituusVarFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double lituus_var_a;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("lituus_var");

APO_VARIABLES(
    VAR_REAL(lituus_var_a, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double theta = atan2(FTy, FTx);
    double abs_theta = max(fabs(theta), 1e-4);
    double new_r = (VAR(lituus_var_a) * VAR(lituus_var_a)) / abs_theta;
    new_r = sqrt(max(new_r, 0.0));
    FPx += VVAR * new_r * cos(theta);
    FPy += VVAR * new_r * sin(theta);
    
    return TRUE;
}
