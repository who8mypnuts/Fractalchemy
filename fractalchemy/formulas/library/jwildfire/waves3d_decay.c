/*
    Fractalchemy formula library — translated from the JWildfire variation
        Waves3dDecayFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double waves3d_decay_freq;
    double waves3d_decay_decay;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("waves3d_decay");

APO_VARIABLES(
    VAR_REAL(waves3d_decay_freq, 3),
    VAR_REAL(waves3d_decay_decay, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double wd_r = sqrt(FTx * FTx + FTy * FTy);
    double wd_theta = atan2(FTy, FTx);
    double wd_nr = wd_r + sin(wd_r * VAR(waves3d_decay_freq)) * exp(- wd_r * VAR(waves3d_decay_decay));
    FPx += VVAR * wd_nr * cos(wd_theta);
    FPy += VVAR * wd_nr * sin(wd_theta);
    
    return TRUE;
}
