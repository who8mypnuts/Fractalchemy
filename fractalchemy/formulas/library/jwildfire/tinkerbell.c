/*
    Fractalchemy formula library — translated from the JWildfire variation
        TinkerbellFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double tinkerbell_a;
    double tinkerbell_b;
    double tinkerbell_c;
    double tinkerbell_d;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("tinkerbell");

APO_VARIABLES(
    VAR_REAL(tinkerbell_a, -0.3),
    VAR_REAL(tinkerbell_b, -0.6013),
    VAR_REAL(tinkerbell_c, 2),
    VAR_REAL(tinkerbell_d, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double nx = FTx * FTx - FTy * FTy + VAR(tinkerbell_a) * FTx + VAR(tinkerbell_b) * FTy;
    double ny = 2.0 * FTx * FTy + VAR(tinkerbell_c) * FTx + VAR(tinkerbell_d) * FTy;
    FPx += VVAR * nx;
    FPy += VVAR * ny;
    
    return TRUE;
}
