/*
    Fractalchemy formula library — translated from the JWildfire variation
        Csch2_BSFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double csch2_bs_x1;
    double csch2_bs_x2;
    double csch2_bs_y1;
    double csch2_bs_y2;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("csch2_bs");

APO_VARIABLES(
    VAR_REAL(csch2_bs_x1, 1),
    VAR_REAL(csch2_bs_x2, 1),
    VAR_REAL(csch2_bs_y1, 1),
    VAR_REAL(csch2_bs_y2, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double cschsin = sin(FTy * VAR(csch2_bs_y1));
    double cschcos = cos(FTy * VAR(csch2_bs_y2));
    double cschsinh = sinh(FTx * VAR(csch2_bs_x1));
    double cschcosh = cosh(FTx * VAR(csch2_bs_x2));
    double d = (cosh(2.0 * FTx) - cos(2.0 * FTy));
    if(d == 0) {
        return;
    }
    double cschden = 2.0 / d;
    FPx += VVAR * cschden * cschsinh * cschcos;
    FPy -= VVAR * cschden * cschcosh * cschsin;
    
    return TRUE;
}
