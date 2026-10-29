/*
    Fractalchemy formula library — translated from the JWildfire variation
        CliffordFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double clifford_js_a;
    double clifford_js_b;
    double clifford_js_c;
    double clifford_js_d;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("clifford_js");

APO_VARIABLES(
    VAR_REAL(clifford_js_a, -1.4),
    VAR_REAL(clifford_js_b, 1.6),
    VAR_REAL(clifford_js_c, 1),
    VAR_REAL(clifford_js_d, 0.7)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double x = sin(VAR(clifford_js_a) * FTy) + VAR(clifford_js_c) * cos(VAR(clifford_js_a) * FTx);
    double y = sin(VAR(clifford_js_b) * FTx) + VAR(clifford_js_d) * cos(VAR(clifford_js_b) * FTy);
    FPx += x * VVAR;
    FPy += y * VVAR;
    
    return TRUE;
}
