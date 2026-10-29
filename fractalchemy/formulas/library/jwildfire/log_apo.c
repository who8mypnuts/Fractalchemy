/*
    Fractalchemy formula library — translated from the JWildfire variation
        LogApoFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double log_apo_base;
    double log_apo__denom;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("log_apo");

APO_VARIABLES(
    VAR_REAL(log_apo_base, 2.71828)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(log_apo__denom) = 0.5 / log(VAR(log_apo_base));
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    FPx += VVAR * log(sqr(FTx) + sqr(FTy)) * VAR(log_apo__denom);
    FPy += VVAR * atan2(FTy, FTx);
    
    return TRUE;
}
