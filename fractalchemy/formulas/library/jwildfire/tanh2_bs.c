/*
    Fractalchemy formula library — translated from the JWildfire variation
        Tanh2_BSFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double tanh2_bs_x1;
    double tanh2_bs_x2;
    double tanh2_bs_y1;
    double tanh2_bs_y2;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("tanh2_bs");

APO_VARIABLES(
    VAR_REAL(tanh2_bs_x1, 2),
    VAR_REAL(tanh2_bs_x2, 2),
    VAR_REAL(tanh2_bs_y1, 2),
    VAR_REAL(tanh2_bs_y2, 2)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double tanhsin = sin(VAR(tanh2_bs_y1) * FTy);
    double tanhcos = cos(VAR(tanh2_bs_y2) * FTy);
    double tanhsinh = sinh(VAR(tanh2_bs_x1) * FTx);
    double tanhcosh = cosh(VAR(tanh2_bs_x2) * FTx);
    double d = (tanhcos + tanhcosh);
    if(d == 0) {
        return;
    }
    double tanhden = 1.0 / d;
    FPx += VVAR * tanhden * tanhsinh;
    FPy += VVAR * tanhden * tanhsin;
    
    return TRUE;
}
