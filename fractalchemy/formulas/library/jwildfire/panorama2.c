/*
    Fractalchemy formula library — translated from the JWildfire variation
        Panorama2Func.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

#include "apoplugin.h"

APO_PLUGIN("panorama2");

APO_NOVARIABLES;

#define M_1_PI (1.0 / M_PI)

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double aux = 1.0 / (sqrt(FTx * FTx + FTy * FTy) + 1.0);
    double x1 = FTx * aux;
    double y1 = FTy * aux;
    aux = sqrt(x1 * x1 + y1 * y1);
    FPx += VVAR * (atan2(x1, y1)) * M_1_PI;
    FPy += VVAR * (aux - 0.5);
    
    return TRUE;
}
