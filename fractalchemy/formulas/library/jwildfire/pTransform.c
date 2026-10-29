/*
    Fractalchemy formula library — translated from the JWildfire variation
        PTransformFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double pTransform_rotate;
    int pTransform_power;
    double pTransform_move;
    double pTransform_split;
    int pTransform_use_log;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("pTransform");

APO_VARIABLES(
    VAR_REAL(pTransform_rotate, 0.3),
    VAR_INTEGER(pTransform_power, 2),
    VAR_REAL(pTransform_move, 0.4),
    VAR_REAL(pTransform_split, 0),
    VAR_INTEGER(pTransform_use_log, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double rho, theta;
    rho = (VAR(pTransform_use_log) != 0) ? log((sqrt(FTx * FTx + FTy * FTy) + EPS)) / VAR(pTransform_power) + VAR(pTransform_move) : (sqrt(FTx * FTx + FTy * FTy) + EPS) / VAR(pTransform_power) + VAR(pTransform_move);
    theta = atan2(FTy, FTx) + VAR(pTransform_rotate);
    if(FTx >= 0.0) rho += VAR(pTransform_split);
    else rho -= VAR(pTransform_split);
    if(VAR(pTransform_use_log) != 0) rho = exp(rho);
    FPx += VVAR * rho * cos(theta);
    FPy += VVAR * rho * sin(theta);
    
    return TRUE;
}
