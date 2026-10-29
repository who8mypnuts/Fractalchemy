/*
    Fractalchemy formula library — translated from the JWildfire variation
        ChainmailFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double chainmail_scale;
    double chainmail_ring_ratio;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("chainmail");

APO_VARIABLES(
    VAR_REAL(chainmail_scale, 3),
    VAR_REAL(chainmail_ring_ratio, 0.35)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double cm_cx = FTx * VAR(chainmail_scale);
    double cm_cy = FTy * VAR(chainmail_scale);
    double cm_row = floor(cm_cy);
    double cm_row_mod = cm_row % 2.0;
    if(cm_row_mod < 0) cm_row_mod += 2.0;
    double cm_offset = cm_row_mod < 0.5 ? 0.5 : 0.0;
    double cm_lx = (cm_cx + cm_offset) - floor(cm_cx + cm_offset) - 0.5;
    double cm_ly = cm_cy - floor(cm_cy) - 0.5;
    double cm_r = sqrt(cm_lx * cm_lx + cm_ly * cm_ly);
    double cm_s = cm_r < VAR(chainmail_ring_ratio) ? VAR(chainmail_ring_ratio) / (cm_r + 1e-6) : 1.0;
    FPx += VVAR * (cm_lx * cm_s) / VAR(chainmail_scale);
    FPy += VVAR * (cm_ly * cm_s) / VAR(chainmail_scale);
    
    return TRUE;
}
