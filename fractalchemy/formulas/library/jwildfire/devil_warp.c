/*
    Fractalchemy formula library — translated from the JWildfire variation
        DevilWarpFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double devil_warp_a;
    double devil_warp_b;
    double devil_warp_effect;
    double devil_warp_warp;
    double devil_warp_rmin;
    double devil_warp_rmax;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("devil_warp");

APO_VARIABLES(
    VAR_REAL(devil_warp_a, 2),
    VAR_REAL(devil_warp_b, 1),
    VAR_REAL(devil_warp_effect, 1),
    VAR_REAL(devil_warp_warp, 0.5),
    VAR_REAL(devil_warp_rmin, -0.24),
    VAR_REAL(devil_warp_rmax, 100)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double xx = FTx;
    double yy = FTy;
    double r2 = 1.0 / (xx * xx + yy * yy);
    double r = pow(xx * xx + r2 * VAR(devil_warp_b) * yy * yy, VAR(devil_warp_warp)) - pow(yy * yy + r2 * VAR(devil_warp_a) * xx * xx, VAR(devil_warp_warp));
    if(r > VAR(devil_warp_rmax)) r = VAR(devil_warp_rmax);
    else if(r < VAR(devil_warp_rmin)) r = VAR(devil_warp_rmin);
    r = VAR(devil_warp_effect) * (r);
    FPx += xx * (1 + r);
    FPy += yy * (1 + r);
    
    return TRUE;
}
