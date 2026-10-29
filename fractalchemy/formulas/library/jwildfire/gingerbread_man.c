/*
    Fractalchemy formula library — translated from the JWildfire variation
        GingerBreadManFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

// keeps a private orbit between points (JWildfire fields updated per point): the statics below
#include "apoplugin.h"

APO_PLUGIN("gingerbread_man");

APO_NOVARIABLES;

static double x0 = -0.1;
static double y0 = 0;

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double xn = 1 - y0 + fabs(x0);
    double yn = x0;
    FPx = xn * VVAR;
    FPy = yn * VVAR;
    
    x0 = xn;
    y0 = yn;
    return TRUE;
}
