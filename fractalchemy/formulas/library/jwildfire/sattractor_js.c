/*
    Fractalchemy formula library — translated from the JWildfire variation
        SattractorFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    int sattractor_js_m;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("sattractor_js");

APO_VARIABLES(
    VAR_INTEGER(sattractor_js_m, 10)
);

int PluginVarPrepare(Variation* vp)
{
    double a[13];
    double b[13];
    for(int i = 1;
    i <= VAR(sattractor_js_m);
    i++) {
        a[i] = cos(2.0 * M_PI * (double) i / (double) VAR(sattractor_js_m));
        b[i] = sin(2.0 * M_PI * (double) i / (double) VAR(sattractor_js_m));
    }
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double a[13];
    double b[13];
    double x, y;
    int l = (int)(random01() * (double) VAR(sattractor_js_m)) + 1;
    if(random01() < 0.5) {
        x = FTx / 2.0 + a[l];
        y = FTy / 2.0 + b[l];
    } else {
        x = FTx * a[l] + FTy * b[l] + FTx * FTx * b[l];
        y = FTy * a[l] - FTx * b[l] + FTx * FTx * a[l];
    }
    x /= 2.0;
    y /= 2.0;
    FPx += x * VVAR;
    FPy += y * VVAR;
    
    return TRUE;
}
