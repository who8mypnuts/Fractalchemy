/*
    Fractalchemy formula library — translated from the JWildfire variation
        GingerbreadFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

#include "apoplugin.h"

APO_PLUGIN("gingerbread");

APO_NOVARIABLES;

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double nx = 1.0 - FTy + fabs(FTx);
    double ny = FTx;
    FPx += VVAR * nx;
    FPy += VVAR * ny;
    
    return TRUE;
}
