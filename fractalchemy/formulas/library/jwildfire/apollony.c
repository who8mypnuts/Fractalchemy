/*
    Fractalchemy formula library — translated from the JWildfire variation
        ApollonyFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

#include "apoplugin.h"

APO_PLUGIN("apollony");

APO_NOVARIABLES;

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double x, y, a0, b0, f1x, f1y;
    double r = sqrt(3.0);
    a0 = 3.0 * (1.0 + r - FTx) / (pow(1.0 + r - FTx, 2.0) + FTy * FTy) - (1.0 + r) / (2.0 + r);
    b0 = 3.0 * FTy / (pow(1.0 + r - FTx, 2.0) + FTy * FTy);
    f1x = a0 / (a0 * a0 + b0 * b0);
    f1y = - b0 / (a0 * a0 + b0 * b0);
    int w = (int)(4.0 * random01());
    if((w % 3) == 0) {
        x = a0;
        y = b0;
    } else if((w % 3) == 1) {
        x = - f1x / 2.0 - f1y * r / 2.0;
        y = f1x * r / 2.0 - f1y / 2.0;
    } else {
        x = - f1x / 2.0 + f1y * r / 2.0;
        y = - f1x * r / 2.0 - f1y / 2.0;
    }
    FPx += x * VVAR;
    FPy += y * VVAR;
    
    return TRUE;
}
