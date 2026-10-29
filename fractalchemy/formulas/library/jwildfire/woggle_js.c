/*
    Fractalchemy formula library — translated from the JWildfire variation
        WoggleFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    int woggle_js_m;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("woggle_js");

APO_VARIABLES(
    VAR_INTEGER(woggle_js_m, 2)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double a[25];
    double b[25];
    double x, y;
    double r = sqrt(1.25) * sqrt((double) VAR(woggle_js_m));
    int c = (int)((double) VAR(woggle_js_m) * random01());
    double ra = 1.0 / (sqrt(3.0) * sqrt(FTx * FTx + FTy * FTy));
    if(c % 2 == 0) {
        x = - FTx / r + ra * FTy / r + a[c];
        y = - ra * FTx / r - FTy / r + b[c];
    } else {
        x = FTx / r + ra * FTy / r + a[c];
        y = - ra * FTx / r + FTy / r + b[c];
    }
    FPx += x * VVAR;
    FPy += y * VVAR;
    
    return TRUE;
}
