/*
    Fractalchemy formula library — translated from the JWildfire variation
        TwistRibbonFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double twist_ribbon_freq;
    double twist_ribbon_width;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("twist_ribbon");

APO_VARIABLES(
    VAR_REAL(twist_ribbon_freq, 3),
    VAR_REAL(twist_ribbon_width, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double tw_twist = VAR(twist_ribbon_freq) * FTx;
    double tw_c = cos(tw_twist);
    double tw_s = sin(tw_twist);
    FPx += VVAR * (tw_c * FTx - tw_s * FTy * VAR(twist_ribbon_width));
    FPy += VVAR * (tw_s * FTx + tw_c * FTy * VAR(twist_ribbon_width));
    
    return TRUE;
}
