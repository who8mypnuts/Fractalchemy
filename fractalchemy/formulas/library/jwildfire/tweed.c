/*
    Fractalchemy formula library — translated from the JWildfire variation
        TweedFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double tweed_freq;
    double tweed_amp;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("tweed");

APO_VARIABLES(
    VAR_REAL(tweed_freq, 3),
    VAR_REAL(tweed_amp, 0.2)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double tw_d1 = ((FTx + FTy) * VAR(tweed_freq)) - floor((FTx + FTy) * VAR(tweed_freq));
    double tw_d2 = ((FTx - FTy) * VAR(tweed_freq)) - floor((FTx - FTy) * VAR(tweed_freq));
    double tw_p = sin(tw_d1 * M_PI);
    double tw_c = sin(tw_d2 * M_PI);
    double sign_tw_c = (tw_c == 0.0) ? 0.0 : (tw_c < 0.0 ? - 1.0 : 1.0);
    double sign_tw_p = (tw_p == 0.0) ? 0.0 : (tw_p < 0.0 ? - 1.0 : 1.0);
    FPx += VVAR * (FTx + VAR(tweed_amp) * tw_p * sign_tw_c);
    FPy += VVAR * (FTy - VAR(tweed_amp) * tw_c * sign_tw_p);
    
    return TRUE;
}
