/*
    Fractalchemy formula library — translated from the JWildfire variation
        WaveFuncFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double wave_func_freq;
    double wave_func_phase;
    double wave_func_decay;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("wave_func");

APO_VARIABLES(
    VAR_REAL(wave_func_freq, 3),
    VAR_REAL(wave_func_phase, 1),
    VAR_REAL(wave_func_decay, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double wf_r = sqrt(FTx * FTx + FTy * FTy);
    double wf_a = atan2(FTy, FTx);
    double wf_psi = cos(VAR(wave_func_freq) * wf_r) * exp(- VAR(wave_func_decay) * wf_r) * cos(VAR(wave_func_phase) * wf_a);
    double wf_nr = wf_r + wf_psi;
    FPx += VVAR * wf_nr * cos(wf_a);
    FPy += VVAR * wf_nr * sin(wf_a);
    
    return TRUE;
}
