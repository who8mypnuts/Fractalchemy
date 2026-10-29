/*
    Fractalchemy formula library — translated from the JWildfire variation
        ChrysanthemumFunc.java
        by Jesus Sosa
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

#include "apoplugin.h"

APO_PLUGIN("chrysanthemum");

APO_NOVARIABLES;

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double u = 21.0 * M_PI * random01();
    double p4 = sin(17.0 * u / 3.0);
    double p8 = sin(2.0 * cos(3.0 * u) - 28.0 * u);
    double r = 5.0 * (1 + sin(11.0 * u / 5.0)) - 4.0 * p4 * p4 * p4 * p4 * p8 * p8 * p8 * p8 * p8 * p8 * p8 * p8;
    r *= VVAR * 0.1;
    FPx += r * cos(u);
    FPy += r * sin(u);
    
    return TRUE;
}
