/*
    Fractalchemy formula library — translated from the JWildfire variation
        GradientWarpFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double gradient_warp_freq;
    double gradient_warp_amp;
    double gradient_warp_seed;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("gradient_warp");

APO_VARIABLES(
    VAR_REAL(gradient_warp_freq, 2),
    VAR_REAL(gradient_warp_amp, 0.5),
    VAR_REAL(gradient_warp_seed, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double gw_px = VAR(gradient_warp_freq) * FTx + VAR(gradient_warp_seed);
    double gw_py = VAR(gradient_warp_freq) * FTy + VAR(gradient_warp_seed) * 1.3;
    double gw_dx = VAR(gradient_warp_amp) * cos(gw_px) * sin(gw_py);
    double gw_dy = VAR(gradient_warp_amp) * sin(gw_px) * cos(gw_py);
    FPx += VVAR * gw_dx;
    FPy += VVAR * gw_dy;
    
    return TRUE;
}
