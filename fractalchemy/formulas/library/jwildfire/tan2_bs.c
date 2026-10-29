/*
    Fractalchemy formula library — translated from the JWildfire variation
        Tan2_BSFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double tan2_bs_x1;
    double tan2_bs_x2;
    double tan2_bs_y1;
    double tan2_bs_y2;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("tan2_bs");

APO_VARIABLES(
    VAR_REAL(tan2_bs_x1, 2),
    VAR_REAL(tan2_bs_x2, 2),
    VAR_REAL(tan2_bs_y1, 2),
    VAR_REAL(tan2_bs_y2, 2)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double tansin = sin(VAR(tan2_bs_x1) * FTx);
    double tancos = cos(VAR(tan2_bs_x2) * FTx);
    double tansinh = sinh(VAR(tan2_bs_y1) * FTy);
    double tancosh = cosh(VAR(tan2_bs_y2) * FTy);
    double d = (tancos + tancosh);
    if(d == 0) {
        return;
    }
    double tanden = 1.0 / d;
    FPx += VVAR * tanden * tansin;
    FPy += VVAR * tanden * tansinh;
    
    return TRUE;
}
