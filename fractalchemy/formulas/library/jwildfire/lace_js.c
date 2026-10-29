/*
    Fractalchemy formula library — translated from the JWildfire variation
        LaceFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

#include "apoplugin.h"

APO_PLUGIN("lace_js");

APO_NOVARIABLES;

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double x = 0.5, y = 0.75;
    double w = 0.0;
    double r = 2.0;
    double r0 = sqrt(FTx * FTx + FTy * FTy);
    double weight = random01();
    if(weight > 0.75) {
        w = atan2(FTy, FTx - 1.0);
        y = - r0 * cos(w) / r + 1.0;
        x = - r0 * sin(w) / r;
    } else if(weight > 0.50) {
        w = atan2(FTy - sqrt(3.0) / 2.0, FTx + 0.5);
        y = - r0 * cos(w) / r - 0.5;
        x = - r0 * sin(w) / r + sqrt(3.0) / 2.0;
    } else if(weight > 0.25) {
        w = atan2(FTy + sqrt(3.0) / 2.0, FTx + 0.5);
        y = - r0 * cos(w) / r - 0.5;
        x = - r0 * sin(w) / r - sqrt(3.0) / 2.0;
    } else {
        w = atan2(FTy, FTx);
        y = - r0 * cos(w) / r;
        x = - r0 * sin(w) / r;
    }
    FPx += x * VVAR;
    FPy += y * VVAR;
    return TRUE;
}
