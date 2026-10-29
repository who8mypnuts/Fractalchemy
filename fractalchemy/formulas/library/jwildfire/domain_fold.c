/*
    Fractalchemy formula library — translated from the JWildfire variation
        DomainFoldFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double domain_fold_fold_x;
    double domain_fold_fold_y;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("domain_fold");

APO_VARIABLES(
    VAR_REAL(domain_fold_fold_x, 1),
    VAR_REAL(domain_fold_fold_y, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double df_fx = max(fabs(VAR(domain_fold_fold_x)), 1e-4);
    double df_fy = max(fabs(VAR(domain_fold_fold_y)), 1e-4);
    double nx = FTx;
    double ny = FTy;
    if(nx > df_fx) nx = 2.0 * df_fx - nx;
    else if(nx < - df_fx) nx = - 2.0 * df_fx - nx;
    if(ny > df_fy) ny = 2.0 * df_fy - ny;
    else if(ny < - df_fy) ny = - 2.0 * df_fy - ny;
    FPx += VVAR * nx;
    FPy += VVAR * ny;
    
    return TRUE;
}
