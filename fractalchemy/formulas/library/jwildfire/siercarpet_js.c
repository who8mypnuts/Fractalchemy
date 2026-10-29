/*
    Fractalchemy formula library — translated from the JWildfire variation
        SiercarpetFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

// keeps a private orbit between points (JWildfire fields updated per point): the statics below
typedef struct {
    int siercarpet_js_m;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("siercarpet_js");

APO_VARIABLES(
    VAR_INTEGER(siercarpet_js_m, 3)
);

static int d = 0;

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double a[25];
    double b[25];
    double x = 1.0, y = 1.0;
    for(int i = 1;
    i <= VAR(siercarpet_js_m);
    i++) {
        a[2 * i - 1] = cos(2.0 * M_PI * (double) i / (double) VAR(siercarpet_js_m));
        b[2 * i - 1] = sin(2.0 * M_PI * (double) i / (double) VAR(siercarpet_js_m));
    }
    for(int i = 1;
    i <= VAR(siercarpet_js_m);
    i++) {
        a[2 * i] = (cos(2.0 * M_PI * i / (double) VAR(siercarpet_js_m)) + cos(2.0 * M_PI * (i - 1) / (double) VAR(siercarpet_js_m))) / 2.0;
        b[2 * i] = (sin(2.0 * M_PI * i / (double) VAR(siercarpet_js_m)) + sin(2.0 * M_PI * (i - 1) / (double) VAR(siercarpet_js_m))) / 2.0;
    }
    int l = 1 + (int)(2.0 * (double) VAR(siercarpet_js_m) * random01());
    d = 1;
    x = FTx / 3.0 + (a[l] - b[l]) / sqrt(2.0);
    y = FTy / 3.0 + (a[l] + b[l]) / sqrt(2.0);
    FPx += x * VVAR;
    FPy += y * VVAR;
    
    return TRUE;
}
