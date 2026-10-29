/*
    Fractalchemy formula library — translated from the JWildfire variation
        BubbleWFFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

#include "apoplugin.h"

APO_PLUGIN("bubble_wf");

APO_NOVARIABLES;

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double r = ((FTx * FTx + FTy * FTy) / 4.0 + 1.0);
    double t = VVAR / r;
    FPx += t * FTx;
    FPy += t * FTy;
    if(random01() < 0.5) {
        FPz -= VVAR * (2 / r - 1);
    } else {
        FPz += VVAR * (2 / r - 1);
    }
    return TRUE;
}
