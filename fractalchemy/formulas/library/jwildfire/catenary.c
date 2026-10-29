/*
    Fractalchemy formula library — translated from the JWildfire variation
        CatenaryFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double catenary_a;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("catenary");

APO_VARIABLES(
    VAR_REAL(catenary_a, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double cat_a = max(fabs(VAR(catenary_a)), 0.001);
    FPx += VVAR * FTx;
    FPy += VVAR * cat_a * cosh(FTx / cat_a);
    
    return TRUE;
}
