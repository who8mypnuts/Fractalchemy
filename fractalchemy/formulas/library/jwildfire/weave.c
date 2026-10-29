/*
    Fractalchemy formula library — translated from the JWildfire variation
        WeaveFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double weave_scale;
    double weave_warp;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("weave");

APO_VARIABLES(
    VAR_REAL(weave_scale, 0.5),
    VAR_REAL(weave_warp, 0.3)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double wv_scale = max(fabs(VAR(weave_scale)), 0.01);
    double wv_col = floor(FTx / wv_scale);
    double wv_row = floor(FTy / wv_scale);
    double wv_lx = FTx / wv_scale - wv_col - 0.5;
    double wv_ly = FTy / wv_scale - wv_row - 0.5;
    double col_row_mod = (wv_col + wv_row) % 2.0;
    if(col_row_mod < 0.0) col_row_mod += 2.0;
    double wv_over = 2.0 * col_row_mod - 1.0;
    double wv_dx = VAR(weave_warp) * wv_over * sin(M_PI * wv_ly);
    double wv_dy = VAR(weave_warp) * (- wv_over) * sin(M_PI * wv_lx);
    FPx += VVAR * (FTx + wv_dx * wv_scale);
    FPy += VVAR * (FTy + wv_dy * wv_scale);
    
    return TRUE;
}
