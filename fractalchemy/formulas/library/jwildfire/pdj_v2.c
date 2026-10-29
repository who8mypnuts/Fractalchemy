/*
    Fractalchemy formula library — translated from the JWildfire variation
        PDJv2Func.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double pdj_v2_a;
    double pdj_v2_b;
    double pdj_v2_c;
    double pdj_v2_d;
    double pdj_v2_e;
    double pdj_v2_f;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("pdj_v2");

APO_VARIABLES(
    VAR_REAL(pdj_v2_a, -0.7),
    VAR_REAL(pdj_v2_b, 1),
    VAR_REAL(pdj_v2_c, 0),
    VAR_REAL(pdj_v2_d, 2),
    VAR_REAL(pdj_v2_e, 0),
    VAR_REAL(pdj_v2_f, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    FPx += VVAR * (sin(VAR(pdj_v2_a) * FTy + VAR(pdj_v2_e)) - cos(VAR(pdj_v2_b) * FTx + VAR(pdj_v2_e)));
    FPy += VVAR * (sin(VAR(pdj_v2_c) * FTx + VAR(pdj_v2_f)) - cos(VAR(pdj_v2_d) * FTy + VAR(pdj_v2_f)));
    
    return TRUE;
}
