/*
    Fractalchemy formula library — translated from the JWildfire variation
        SvenssonFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double svensson_js_a;
    double svensson_js_b;
    double svensson_js_c;
    double svensson_js_d;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("svensson_js");

APO_VARIABLES(
    VAR_REAL(svensson_js_a, 1.4),
    VAR_REAL(svensson_js_b, 1.56),
    VAR_REAL(svensson_js_c, 1.4),
    VAR_REAL(svensson_js_d, -6.56)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double x = VAR(svensson_js_d) * sin(VAR(svensson_js_a) * FTx) - sin(VAR(svensson_js_b) * FTy);
    double y = VAR(svensson_js_c) * cos(VAR(svensson_js_a) * FTx) + cos(VAR(svensson_js_b) * FTy);
    FPx = x * VVAR;
    FPy = y * VVAR;
    
    return TRUE;
}
