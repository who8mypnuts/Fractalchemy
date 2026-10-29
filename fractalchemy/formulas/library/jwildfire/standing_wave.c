/*
    Fractalchemy formula library — translated from the JWildfire variation
        StandingWaveFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double standing_wave_freq_x;
    double standing_wave_freq_y;
    double standing_wave_amp;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("standing_wave");

APO_VARIABLES(
    VAR_REAL(standing_wave_freq_x, 3),
    VAR_REAL(standing_wave_freq_y, 3),
    VAR_REAL(standing_wave_amp, 0.3)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double dx = VAR(standing_wave_amp) * sin(VAR(standing_wave_freq_x) * M_PI * FTx) * cos(VAR(standing_wave_freq_y) * M_PI * FTy);
    double dy = VAR(standing_wave_amp) * cos(VAR(standing_wave_freq_x) * M_PI * FTx) * sin(VAR(standing_wave_freq_y) * M_PI * FTy);
    FPx += VVAR * (FTx + dx);
    FPy += VVAR * (FTy + dy);
    
    return TRUE;
}
