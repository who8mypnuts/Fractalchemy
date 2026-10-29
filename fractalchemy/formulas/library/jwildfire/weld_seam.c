/*
    Fractalchemy formula library — translated from the JWildfire variation
        WeldSeamFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double weld_seam_pitch;
    double weld_seam_height;
    double weld_seam_width;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("weld_seam");

APO_VARIABLES(
    VAR_REAL(weld_seam_pitch, 0.5),
    VAR_REAL(weld_seam_height, 0.2),
    VAR_REAL(weld_seam_width, 0.2)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double ws_bx = floor(FTx / VAR(weld_seam_pitch) + 0.5) * VAR(weld_seam_pitch);
    double ws_dx = FTx - ws_bx;
    double ws_dist2 = ws_dx * ws_dx + FTy * FTy;
    double ws_push = VAR(weld_seam_height) * exp(- ws_dist2 / (VAR(weld_seam_width) * VAR(weld_seam_width) + 0.001));
    double ws_len = sqrt(ws_dist2) + 0.001;
    FPx += VVAR * (FTx + ws_push * ws_dx / ws_len);
    FPy += VVAR * (FTy + ws_push * FTy / ws_len);
    
    return TRUE;
}
