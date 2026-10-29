/*
    Fractalchemy formula library — translated from the JWildfire variation
        SimplexWarpFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double simplex_warp_freq;
    double simplex_warp_amp;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("simplex_warp");

APO_VARIABLES(
    VAR_REAL(simplex_warp_freq, 2),
    VAR_REAL(simplex_warp_amp, 0.4)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double sw_x = VAR(simplex_warp_freq) * FTx;
    double sw_y = VAR(simplex_warp_freq) * FTy;
    double sw_v1 = sin(sw_x * 1.3 + sw_y * 0.7 + sin(sw_x * 0.9 - sw_y * 1.1) * 2.0);
    double sw_v2 = sin(sw_y * 1.1 + sw_x * 0.8 + sin(sw_y * 1.2 + sw_x * 0.6) * 2.0);
    FPx += VVAR * VAR(simplex_warp_amp) * sw_v1;
    FPy += VVAR * VAR(simplex_warp_amp) * sw_v2;
    
    return TRUE;
}
