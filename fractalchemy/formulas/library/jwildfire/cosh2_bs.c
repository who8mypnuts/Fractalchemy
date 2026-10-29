/*
    Fractalchemy formula library — translated from the JWildfire variation
        Cosh2_BSFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double cosh2_bs_x1;
    double cosh2_bs_x2;
    double cosh2_bs_y1;
    double cosh2_bs_y2;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("cosh2_bs");

APO_VARIABLES(
    VAR_REAL(cosh2_bs_x1, 1),
    VAR_REAL(cosh2_bs_x2, 1),
    VAR_REAL(cosh2_bs_y1, 1),
    VAR_REAL(cosh2_bs_y2, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double coshsin = sin(FTy * VAR(cosh2_bs_y1));
    double coshcos = cos(FTy * VAR(cosh2_bs_y2));
    double coshsinh = sinh(FTx * VAR(cosh2_bs_x1));
    double coshcosh = cosh(FTx * VAR(cosh2_bs_x2));
    FPx += VVAR * coshcosh * coshcos;
    FPy += VVAR * coshsinh * coshsin;
    
    return TRUE;
}
