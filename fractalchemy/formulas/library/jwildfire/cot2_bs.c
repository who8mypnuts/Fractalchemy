/*
    Fractalchemy formula library — translated from the JWildfire variation
        Cot2_BSFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double cot2_bs_x1;
    double cot2_bs_x2;
    double cot2_bs_y1;
    double cot2_bs_y2;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("cot2_bs");

APO_VARIABLES(
    VAR_REAL(cot2_bs_x1, 2),
    VAR_REAL(cot2_bs_x2, 2),
    VAR_REAL(cot2_bs_y1, 2),
    VAR_REAL(cot2_bs_y2, 2)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double cotsin = sin(VAR(cot2_bs_x1) * FTx);
    double cotcos = cos(VAR(cot2_bs_x2) * FTx);
    double cotsinh = sinh(VAR(cot2_bs_y1) * FTy);
    double cotcosh = cosh(VAR(cot2_bs_y2) * FTy);
    double cotden = 1.0 / (cotcosh - cotcos);
    FPx += VVAR * cotden * cotsin;
    FPy += VVAR * cotden * - 1 * cotsinh;
    
    return TRUE;
}
