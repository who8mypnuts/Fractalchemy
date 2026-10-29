/*
    Fractalchemy formula library — translated from the JWildfire variation
        Blade3DFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

#include "apoplugin.h"

APO_PLUGIN("blade3D");

APO_NOVARIABLES;

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double r = random01() * VVAR * sqrt(FTx * FTx + FTy * FTy);
    double sinr = sin(r);
    double cosr = cos(r);
    FPx += VVAR * FTx * (cosr + sinr);
    FPy += VVAR * FTx * (cosr - sinr);
    FPz += VVAR * FTy * (sinr - cosr);
    return TRUE;
}
