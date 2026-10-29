/*
    Fractalchemy formula library — translated from the JWildfire variation
        SymmetricIconFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double symmetric_icon_lambda;
    double symmetric_icon_alpha;
    double symmetric_icon_beta;
    double symmetric_icon_omega;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("symmetric_icon");

APO_VARIABLES(
    VAR_REAL(symmetric_icon_lambda, 1.56),
    VAR_REAL(symmetric_icon_alpha, -1),
    VAR_REAL(symmetric_icon_beta, 0.1),
    VAR_REAL(symmetric_icon_omega, -0.82)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double r2 = FTx * FTx + FTy * FTy;
    double nx = VAR(symmetric_icon_lambda) * FTx + VAR(symmetric_icon_alpha) * (FTx * FTx - FTy * FTy) + VAR(symmetric_icon_beta) * r2 * FTx + VAR(symmetric_icon_omega) * FTx * FTy;
    double ny = VAR(symmetric_icon_lambda) * FTy + 2.0 * VAR(symmetric_icon_alpha) * FTx * FTy + VAR(symmetric_icon_beta) * r2 * FTy + VAR(symmetric_icon_omega) * FTx * FTx;
    FPx += VVAR * nx;
    FPy += VVAR * ny;
    
    return TRUE;
}
