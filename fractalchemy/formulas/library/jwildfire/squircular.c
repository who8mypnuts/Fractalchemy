/*
    Fractalchemy formula library — translated from the JWildfire variation
        SquircularFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

#include "apoplugin.h"

APO_PLUGIN("squircular");

APO_NOVARIABLES;

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double u = FTx;
    double v = FTy;
    double r = u * u + v * v;
    double rs = sqrt(r);
    double xs = u > 0 ? 1.0 : - 1.0;
    r = sqrt(VVAR * VVAR * r - 4 * u * u * v * v);
    r = sqrt(1 + u * u / (v * v) - rs / (VVAR * v * v) * r);
    r = r / sqrt(2);
    FPx += xs * r;
    FPy += v / u * r;
    
    return TRUE;
}
