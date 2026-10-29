/*
    Fractalchemy formula library — translated from the JWildfire variation
        ApocarpetFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

#include "apoplugin.h"

APO_PLUGIN("apocarpet_js");

APO_NOVARIABLES;

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double x = 0, y = 0;
    double r = 1.0 / (1.0 + sqrt(2.0));
    double denom = FTx * FTx + FTy * FTy;
    int weight = (int)(6.0 * random01());
    switch(weight) {
        case 0 : x = 2.0 * FTx * FTy / denom;
        y = (FTx * FTx - FTy * FTy) / denom;
        break;
        case 1 : x = FTx * r - r;
        y = FTy * r - r;
        break;
        case 2 : x = FTx * r + r;
        y = FTy * r + r;
        break;
        case 3 : x = FTx * r + r;
        y = FTy * r - r;
        break;
        case 4 : x = FTx * r - r;
        y = FTy * r + r;
        break;
        case 5 : x = (FTx * FTx - FTy * FTy) / denom;
        y = 2.0 * FTx * FTy / denom;
        break;
    }
    FPx += x * VVAR;
    FPy += y * VVAR;
    
    return TRUE;
}
