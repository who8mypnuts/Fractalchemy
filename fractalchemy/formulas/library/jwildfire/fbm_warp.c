/*
    Fractalchemy formula library — translated from the JWildfire variation
        FBMWarpFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double fbm_warp_freq;
    double fbm_warp_amp;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("fbm_warp");

APO_VARIABLES(
    VAR_REAL(fbm_warp_freq, 1),
    VAR_REAL(fbm_warp_amp, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double x = FTx * VAR(fbm_warp_freq);
    double y = FTy * VAR(fbm_warp_freq);
    double dx = VAR(fbm_warp_amp) * (sin(x + 0.7) * cos(y * 1.3) + 0.5 * sin(x * 2.0 + 1.1) * cos(y * 2.6 + 0.2) + 0.25 * sin(x * 4.0 + 2.3) * cos(y * 5.2 + 0.9));
    double dy = VAR(fbm_warp_amp) * (cos(x * 1.1 + 0.3) * sin(y * 0.9 + 0.5) + 0.5 * cos(x * 2.2 + 1.3) * sin(y * 1.8 + 1.1) + 0.25 * cos(x * 4.4 + 2.7) * sin(y * 3.6 + 2.1));
    FPx += VVAR * (FTx + dx);
    FPy += VVAR * (FTy + dy);
    
    return TRUE;
}
