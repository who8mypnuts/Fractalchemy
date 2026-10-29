/*
    Fractalchemy formula library — translated from the JWildfire variation
        Sech2_BSFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double sech2_bs_x1;
    double sech2_bs_x2;
    double sech2_bs_y1;
    double sech2_bs_y2;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("sech2_bs");

APO_VARIABLES(
    VAR_REAL(sech2_bs_x1, 1.25),
    VAR_REAL(sech2_bs_x2, 0.75),
    VAR_REAL(sech2_bs_y1, 1.5),
    VAR_REAL(sech2_bs_y2, 0.75)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double sechsin = sin(FTy * VAR(sech2_bs_y1));
    double sechcos = cos(FTy * VAR(sech2_bs_y2));
    double sechsinh = sinh(FTx * VAR(sech2_bs_x1));
    double sechcosh = cosh(FTx * VAR(sech2_bs_x2));
    double d = (cos(2.0 * FTy) + cosh(2.0 * FTx));
    if(d == 0) {
        return;
    }
    double sechden = 2.0 / d;
    FPx += VVAR * sechden * sechcos * sechcosh;
    FPy -= VVAR * sechden * sechsin * sechsinh;
    
    return TRUE;
}
