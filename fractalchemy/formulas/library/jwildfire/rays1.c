/*
    Fractalchemy formula library — translated from the JWildfire variation
        Rays1Func.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

#include "apoplugin.h"

APO_PLUGIN("rays1");

APO_NOVARIABLES;

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t = sqr(FTx) + sqr(FTy);
    double u = 1.0 / tan(sqrt(t)) + (VVAR * sqr(M_2_PI));
    FPx = VVAR * u * t / FTx;
    FPy = VVAR * u * t / FTy;
    
    return TRUE;
}
