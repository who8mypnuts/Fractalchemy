/*
    Fractalchemy formula library — translated from the JWildfire variation
        Lace2Func.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double lace_freq;
    double lace_amp;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("lace");

APO_VARIABLES(
    VAR_REAL(lace_freq, 3),
    VAR_REAL(lace_amp, 0.3)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double lc_freq = max(fabs(VAR(lace_freq)), 0.01);
    double lc_nx = VAR(lace_amp) * sin(lc_freq * FTy);
    double lc_ny = VAR(lace_amp) * sin(lc_freq * FTx);
    FPx += VVAR * (FTx + lc_nx);
    FPy += VVAR * (FTy + lc_ny);
    
    return TRUE;
}
