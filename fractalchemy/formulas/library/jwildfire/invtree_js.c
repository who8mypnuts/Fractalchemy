/*
    Fractalchemy formula library — translated from the JWildfire variation
        InvTreeFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

#include "apoplugin.h"

APO_PLUGIN("invtree_js");

APO_NOVARIABLES;

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double x, y;
    if(random01() < 0.333) {
        x = FTx / 2.0;
        y = FTy / 2.0;
    } else if(random01() < 0.666) {
        x = 1.0 / (FTx + 1);
        y = FTy / (FTy + 1.0);
    } else {
        x = FTx / (FTx + 1);
        y = 1.0 / (FTy + 1.0);
    }
    FPx += x * VVAR;
    FPy += y * VVAR;
    
    return TRUE;
}
