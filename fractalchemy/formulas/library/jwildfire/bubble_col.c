/*
    Fractalchemy formula library — translated from the JWildfire variation
        BubbleColFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double bubble_col_freq;
    double bubble_col_amp;
    double bubble_col_rise;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("bubble_col");

APO_VARIABLES(
    VAR_REAL(bubble_col_freq, 4),
    VAR_REAL(bubble_col_amp, 0.3),
    VAR_REAL(bubble_col_rise, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double bc_freq = max(fabs(VAR(bubble_col_freq)), 0.01);
    double bc_col = round(FTx * bc_freq) / bc_freq;
    double bc_phase = bc_col * 2.39996323;
    double bc_sway = VAR(bubble_col_amp) * sin(bc_freq * FTy + bc_phase);
    FPx += VVAR * (bc_col + bc_sway);
    FPy += VVAR * (FTy + VAR(bubble_col_rise) / (bc_freq + 1e-4));
    
    return TRUE;
}
