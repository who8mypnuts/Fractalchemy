/*
    Fractalchemy formula library — translated from the JWildfire variation
        MitosisFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double mitosis_sep;
    double mitosis_width;
    double mitosis_phase;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("mitosis");

APO_VARIABLES(
    VAR_REAL(mitosis_sep, 1),
    VAR_REAL(mitosis_width, 0.5),
    VAR_REAL(mitosis_phase, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double mi_w = max(fabs(VAR(mitosis_width)), 0.01);
    double mi_ca = cos(VAR(mitosis_phase));
    double mi_sa = sin(VAR(mitosis_phase));
    double mi_u = FTx * mi_ca + FTy * mi_sa;
    double mi_v = - FTx * mi_sa + FTy * mi_ca;
    double mi_pull = tanh(mi_u / mi_w);
    double mi_new_u = mi_pull * VAR(mitosis_sep) * 0.5;
    double mi_neck = 1.0 - 0.5 * exp(- (mi_u * mi_u) / (mi_w * mi_w));
    double mi_new_v = mi_v * mi_neck;
    FPx += VVAR * (mi_new_u * mi_ca - mi_new_v * mi_sa);
    FPy += VVAR * (mi_new_u * mi_sa + mi_new_v * mi_ca);
    
    return TRUE;
}
