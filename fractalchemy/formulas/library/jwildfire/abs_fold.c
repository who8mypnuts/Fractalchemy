/*
    Fractalchemy formula library — translated from the JWildfire variation
        AbsFoldFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double abs_fold_fold;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("abs_fold");

APO_VARIABLES(
    VAR_REAL(abs_fold_fold, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double nx = FTx;
    double ny = FTy;
    if(nx > VAR(abs_fold_fold)) {
        nx = 2.0 * VAR(abs_fold_fold) - nx;
    } else if(nx < - VAR(abs_fold_fold)) {
        nx = - 2.0 * VAR(abs_fold_fold) - nx;
    }
    if(ny > VAR(abs_fold_fold)) {
        ny = 2.0 * VAR(abs_fold_fold) - ny;
    } else if(ny < - VAR(abs_fold_fold)) {
        ny = - 2.0 * VAR(abs_fold_fold) - ny;
    }
    FPx += VVAR * nx;
    FPy += VVAR * ny;
    
    return TRUE;
}
