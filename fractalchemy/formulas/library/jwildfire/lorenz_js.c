/*
    Fractalchemy formula library — translated from the JWildfire variation
        LorenzFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double lorenz_js_a;
    double lorenz_js_b;
    double lorenz_js_c;
    double lorenz_js_h;
    double lorenz_js_centerx;
    double lorenz_js_centery;
    double lorenz_js_scale;
    double lorenz_js_bdcs;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("lorenz_js");

APO_VARIABLES(
    VAR_REAL(lorenz_js_a, 10),
    VAR_REAL(lorenz_js_b, 28),
    VAR_REAL(lorenz_js_c, 1.66),
    VAR_REAL(lorenz_js_h, 1e-05),
    VAR_REAL(lorenz_js_centerx, 0),
    VAR_REAL(lorenz_js_centery, 0),
    VAR_REAL(lorenz_js_scale, 1000)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(lorenz_js_bdcs) = 1.0 / (VAR(lorenz_js_scale) == 0.0 ? 10E-6 : VAR(lorenz_js_scale));
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double x = FTx + VAR(lorenz_js_h) * VAR(lorenz_js_a) * (FTy - FTx);
    double y = FTy + VAR(lorenz_js_h) * (FTx * (VAR(lorenz_js_b) - FTz) - FTy);
    double z = FTz + VAR(lorenz_js_h) * (FTx * FTy - VAR(lorenz_js_c) * FTz);
    FPx += x * VVAR;
    FPy += y * VVAR;
    FPz += z * VVAR;
    TC = fmod(fabs(VAR(lorenz_js_bdcs) * (sqr(FPx + VAR(lorenz_js_centerx)) + sqr(FPy + VAR(lorenz_js_centery)))), 1.0);
    return TRUE;
}
