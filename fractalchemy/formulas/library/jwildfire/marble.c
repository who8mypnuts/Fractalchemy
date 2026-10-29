/*
    Fractalchemy formula library — translated from the JWildfire variation
        MarbleFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double marble_freq;
    double marble_amp;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("marble");

APO_VARIABLES(
    VAR_REAL(marble_freq, 2),
    VAR_REAL(marble_amp, 0.3)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double mb_t = VAR(marble_freq) * FTx + VAR(marble_amp) * (sin(VAR(marble_freq) * FTy) + 0.5 * sin(2.0 * VAR(marble_freq) * FTy));
    double mb_dx = VAR(marble_amp) * sin(mb_t);
    double mb_dy = VAR(marble_amp) * 0.3 * cos(VAR(marble_freq) * FTy);
    FPx += VVAR * (FTx + mb_dx);
    FPy += VVAR * (FTy + mb_dy);
    
    return TRUE;
}
