/*
    Fractalchemy formula library — translated from the JWildfire variation
        MercatorFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double mercator_scale;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("mercator");

APO_VARIABLES(
    VAR_REAL(mercator_scale, 1)
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
    double mc_scale = max(fabs(VAR(mercator_scale)), 0.01);
    double mc_lat = clamp(FTy * mc_scale, - 1.5, 1.5);
    double mc_y = log(tan(M_PI * 0.25 + mc_lat * 0.5));
    FPx += VVAR * FTx;
    FPy += VVAR * mc_y / mc_scale;
    
    return TRUE;
}
