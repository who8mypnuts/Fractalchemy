/*
    Fractalchemy formula library — translated from the JWildfire variation
        Cos2_BSFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double cos2_bs_x1;
    double cos2_bs_x2;
    double cos2_bs_y1;
    double cos2_bs_y2;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("cos2_bs");

APO_VARIABLES(
    VAR_REAL(cos2_bs_x1, 1),
    VAR_REAL(cos2_bs_x2, 1),
    VAR_REAL(cos2_bs_y1, 1),
    VAR_REAL(cos2_bs_y2, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double cossin = sin(FTx * VAR(cos2_bs_x1));
    double coscos = cos(FTx * VAR(cos2_bs_x2));
    double cossinh = sinh(FTy * VAR(cos2_bs_y1));
    double coscosh = cosh(FTy * VAR(cos2_bs_y2));
    FPx += VVAR * coscos * coscosh;
    FPy -= VVAR * cossin * cossinh;
    
    return TRUE;
}
