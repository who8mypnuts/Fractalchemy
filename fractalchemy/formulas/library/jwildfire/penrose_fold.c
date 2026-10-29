/*
    Fractalchemy formula library — translated from the JWildfire variation
        PenroseFoldFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double penrose_fold_scale;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("penrose_fold");

APO_VARIABLES(
    VAR_REAL(penrose_fold_scale, 2)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double pf_phi = 1.618033988749895;
    double pf_x = FTx * VAR(penrose_fold_scale);
    double pf_y = FTy * VAR(penrose_fold_scale);
    double pf_u = pf_x + pf_phi * pf_y;
    double pf_v = pf_y - pf_x / pf_phi;
    double pf_fu = pf_u - round(pf_u);
    double pf_fv = pf_v - round(pf_v);
    double pf_nx = (pf_fu - pf_fv / pf_phi) / VAR(penrose_fold_scale);
    double pf_ny = (pf_fv + pf_fu / pf_phi) / VAR(penrose_fold_scale);
    FPx += VVAR * pf_nx;
    FPy += VVAR * pf_ny;
    
    return TRUE;
}
