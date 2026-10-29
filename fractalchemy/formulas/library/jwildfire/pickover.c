/*
    Fractalchemy formula library — translated from the JWildfire variation
        PickoverFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double pickover_a;
    double pickover_b;
    double pickover_c;
    double pickover_d;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("pickover");

APO_VARIABLES(
    VAR_REAL(pickover_a, 1),
    VAR_REAL(pickover_b, 2),
    VAR_REAL(pickover_c, 0.5),
    VAR_REAL(pickover_d, -0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double nx = sin(VAR(pickover_a) * FTy) + VAR(pickover_c) * cos(VAR(pickover_a) * FTx);
    double ny = sin(VAR(pickover_b) * FTx) + VAR(pickover_d) * cos(VAR(pickover_b) * FTy);
    FPx += VVAR * nx;
    FPy += VVAR * ny;
    
    return TRUE;
}
