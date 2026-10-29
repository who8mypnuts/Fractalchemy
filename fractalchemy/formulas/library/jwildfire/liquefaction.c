/*
    Fractalchemy formula library — translated from the JWildfire variation
        LiquefactionFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double liquefaction_freq;
    double liquefaction_amp;
    double liquefaction_phase;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("liquefaction");

APO_VARIABLES(
    VAR_REAL(liquefaction_freq, 3),
    VAR_REAL(liquefaction_amp, 0.3),
    VAR_REAL(liquefaction_phase, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double liq_dx = VAR(liquefaction_amp) * sin(VAR(liquefaction_freq) * FTy + VAR(liquefaction_phase));
    double liq_dy = VAR(liquefaction_amp) * sin(VAR(liquefaction_freq) * FTx + VAR(liquefaction_phase));
    FPx += VVAR * (FTx + liq_dx);
    FPy += VVAR * (FTy + liq_dy);
    
    return TRUE;
}
