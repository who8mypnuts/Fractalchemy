/*
    Fractalchemy formula library — translated from the JWildfire variation
        AuroraCurtainFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double aurora_curtain_freq;
    double aurora_curtain_amp;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("aurora_curtain");

APO_VARIABLES(
    VAR_REAL(aurora_curtain_freq, 2),
    VAR_REAL(aurora_curtain_amp, 0.3)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double ac_dx = VAR(aurora_curtain_amp) * (sin(VAR(aurora_curtain_freq) * FTy) + 0.5 * sin(2.0 * VAR(aurora_curtain_freq) * FTy + 1.1) + 0.25 * sin(3.0 * VAR(aurora_curtain_freq) * FTy + 2.3));
    FPx += VVAR * (FTx + ac_dx);
    FPy += VVAR * FTy;
    
    return TRUE;
}
