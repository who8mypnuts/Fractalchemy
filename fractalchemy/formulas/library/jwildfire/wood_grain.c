/*
    Fractalchemy formula library — translated from the JWildfire variation
        WoodGrainFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double wood_grain_freq;
    double wood_grain_amp;
    double wood_grain_grain;
    double wood_grain_grain_freq;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("wood_grain");

APO_VARIABLES(
    VAR_REAL(wood_grain_freq, 5),
    VAR_REAL(wood_grain_amp, 0.2),
    VAR_REAL(wood_grain_grain, 0.5),
    VAR_REAL(wood_grain_grain_freq, 6)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double wg_r = sqrt(FTx * FTx + FTy * FTy);
    double wg_theta = atan2(FTy, FTx);
    double wg_ring = sin(VAR(wood_grain_freq) * wg_r + VAR(wood_grain_grain) * cos(VAR(wood_grain_grain_freq) * wg_theta));
    double wg_disp = VAR(wood_grain_amp) * wg_ring;
    FPx += VVAR * (FTx + wg_disp * cos(wg_theta));
    FPy += VVAR * (FTy + wg_disp * sin(wg_theta));
    
    return TRUE;
}
