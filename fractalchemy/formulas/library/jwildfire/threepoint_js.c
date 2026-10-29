/*
    Fractalchemy formula library — translated from the JWildfire variation
        ThreePointIFSFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

#include "apoplugin.h"

APO_PLUGIN("threepoint_js");

APO_NOVARIABLES;

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double x, y;
    if(random01() < 0.333) {
        x = FTx / 2.0 - FTy / 2.0 + 0.5;
        y = - FTx / 2.0 - FTy / 2.0 + 0.5;
    } else if(random01() < 0.666) {
        x = FTy;
        y = FTx;
    } else {
        x = - FTy / 2.0 + 0.5;
        y = - FTx / 2.0 + 0.5;
    }
    FPx += x * VVAR;
    FPy += y * VVAR;
    
    return TRUE;
}
