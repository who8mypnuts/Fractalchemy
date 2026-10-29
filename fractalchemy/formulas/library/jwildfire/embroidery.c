/*
    Fractalchemy formula library — translated from the JWildfire variation
        EmbroideryFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double embroidery_scale;
    double embroidery_depth;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("embroidery");

APO_VARIABLES(
    VAR_REAL(embroidery_scale, 3),
    VAR_REAL(embroidery_depth, 0.2)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double emb_cx = FTx * VAR(embroidery_scale);
    double emb_cy = FTy * VAR(embroidery_scale);
    double emb_row = floor(emb_cy);
    double emb_col = floor(emb_cx);
    double row_col_mod = (emb_row + emb_col) % 2.0;
    if(row_col_mod < 0) row_col_mod += 2.0;
    double emb_phase = row_col_mod * M_PI;
    double emb_wx = sin(emb_cx * 6.283185307179586 + emb_phase) * VAR(embroidery_depth);
    double emb_wy = sin(emb_cy * 6.283185307179586 + emb_phase) * VAR(embroidery_depth);
    FPx += VVAR * (FTx + emb_wx / VAR(embroidery_scale));
    FPy += VVAR * (FTy + emb_wy / VAR(embroidery_scale));
    
    return TRUE;
}
