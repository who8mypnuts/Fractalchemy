/*
    Fractalchemy formula library — translated from the JWildfire variation
        PWaveFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double p_wave_freq;
    double p_wave_amp;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("p_wave");

APO_VARIABLES(
    VAR_REAL(p_wave_freq, 4),
    VAR_REAL(p_wave_amp, 0.3)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double pw_dist = sqrt(FTx * FTx + FTy * FTy);
    double pw_compress = 1.0 + VAR(p_wave_amp) * sin(VAR(p_wave_freq) * pw_dist);
    FPx += VVAR * FTx * pw_compress;
    FPy += VVAR * FTy * pw_compress;
    
    return TRUE;
}
