/*
    Fractalchemy formula library — translated from the JWildfire variation
        SuperpositionFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double superposition_freq1;
    double superposition_freq2;
    double superposition_phase;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("superposition");

APO_VARIABLES(
    VAR_REAL(superposition_freq1, 3),
    VAR_REAL(superposition_freq2, 5),
    VAR_REAL(superposition_phase, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double sp_r = sqrt(FTx * FTx + FTy * FTy);
    double sp_wave = 0.5 * (sin(VAR(superposition_freq1) * sp_r) + sin(VAR(superposition_freq2) * sp_r + VAR(superposition_phase)));
    FPx += VVAR * FTx * sp_wave;
    FPy += VVAR * FTy * sp_wave;
    
    return TRUE;
}
