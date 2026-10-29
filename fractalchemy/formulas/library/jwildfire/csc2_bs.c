/*
    Fractalchemy formula library — translated from the JWildfire variation
        Csc2_BSFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double csc2_bs_x1;
    double csc2_bs_x2;
    double csc2_bs_y1;
    double csc2_bs_y2;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("csc2_bs");

APO_VARIABLES(
    VAR_REAL(csc2_bs_x1, 1),
    VAR_REAL(csc2_bs_x2, 1),
    VAR_REAL(csc2_bs_y1, 1),
    VAR_REAL(csc2_bs_y2, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double cscsin = sin(FTx * VAR(csc2_bs_x1));
    double csccos = cos(FTx * VAR(csc2_bs_x2));
    double cscsinh = sinh(FTy * VAR(csc2_bs_y1));
    double csccosh = cosh(FTy * VAR(csc2_bs_y2));
    double d = (cosh(2.0 * FTy) - cos(2.0 * FTx));
    if(d == 0) {
        return;
    }
    double cscden = 2.0 / d;
    FPx += VVAR * cscden * cscsin * csccosh;
    FPy -= VVAR * cscden * csccos * cscsinh;
    
    return TRUE;
}
