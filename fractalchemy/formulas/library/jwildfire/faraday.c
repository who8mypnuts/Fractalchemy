/*
    Fractalchemy formula library — translated from the JWildfire variation
        FaradayFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double faraday_freq;
    int faraday_modes;
    double faraday_amp;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("faraday");

APO_VARIABLES(
    VAR_REAL(faraday_freq, 4),
    VAR_INTEGER(faraday_modes, 4),
    VAR_REAL(faraday_amp, 0.2)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double fa_modes = max(fabs((double) VAR(faraday_modes)), 1.0);
    double fa_r = sqrt(FTx * FTx + FTy * FTy);
    double fa_theta = atan2(FTy, FTx);
    double fa_wave = VAR(faraday_amp) * cos(VAR(faraday_freq) * fa_r) * cos(fa_modes * fa_theta);
    double fa_new_r = fa_r + fa_wave;
    FPx += VVAR * fa_new_r * cos(fa_theta);
    FPy += VVAR * fa_new_r * sin(fa_theta);
    
    return TRUE;
}
