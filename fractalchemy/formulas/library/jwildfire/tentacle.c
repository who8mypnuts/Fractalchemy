/*
    Fractalchemy formula library — translated from the JWildfire variation
        TentacleFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double tentacle_freq;
    double tentacle_amp;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("tentacle");

APO_VARIABLES(
    VAR_REAL(tentacle_freq, 2),
    VAR_REAL(tentacle_amp, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double te_r = sqrt(FTx * FTx + FTy * FTy);
    double te_theta = atan2(FTy, FTx);
    double te_wave = VAR(tentacle_amp) * sin(VAR(tentacle_freq) * te_r);
    double te_new_theta = te_theta + te_wave;
    FPx += VVAR * te_r * cos(te_new_theta);
    FPy += VVAR * te_r * sin(te_new_theta);
    
    return TRUE;
}
