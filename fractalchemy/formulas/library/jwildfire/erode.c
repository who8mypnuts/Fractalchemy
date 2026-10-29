/*
    Fractalchemy formula library — translated from the JWildfire variation
        ErodeFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double erode_strength;
    double erode_scale;
    double erode_rough;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("erode");

APO_VARIABLES(
    VAR_REAL(erode_strength, 0.3),
    VAR_REAL(erode_scale, 2),
    VAR_REAL(erode_rough, 0.5)
);

double clamp(double value, double min, double max)
{
    return max(min, min(max, value));
}

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double er_rough = clamp(VAR(erode_rough), 0.0, 1.0);
    double er_dx0 = VAR(erode_strength) * sin(VAR(erode_scale) * FTx + 0.7 * sin(VAR(erode_scale) * FTy));
    double er_dy0 = VAR(erode_strength) * cos(VAR(erode_scale) * FTy + 0.7 * cos(VAR(erode_scale) * FTx));
    double er_dx1 = er_rough * VAR(erode_strength) * 0.5 * sin(VAR(erode_scale) * 2.1 * FTx - VAR(erode_scale) * FTy * 0.4);
    double er_dy1 = er_rough * VAR(erode_strength) * 0.5 * cos(VAR(erode_scale) * 2.1 * FTy + VAR(erode_scale) * FTx * 0.4);
    FPx += VVAR * (FTx + er_dx0 + er_dx1);
    FPy += VVAR * (FTy + er_dy0 + er_dy1);
    
    return TRUE;
}
