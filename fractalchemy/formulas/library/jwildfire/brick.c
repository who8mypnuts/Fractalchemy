/*
    Fractalchemy formula library — translated from the JWildfire variation
        BrickFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double brick_scale_x;
    double brick_scale_y;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("brick");

APO_VARIABLES(
    VAR_REAL(brick_scale_x, 1),
    VAR_REAL(brick_scale_y, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double br_sx = max(fabs(VAR(brick_scale_x)), 1e-4);
    double br_sy = max(fabs(VAR(brick_scale_y)), 1e-4);
    double row = floor(FTy / br_sy);
    double offset = ((row % 2.0 + 2.0) % 2.0 > 0.5) ? br_sx * 0.5 : 0.0;
    double nx = FTx - (floor((FTx + offset) / br_sx) * br_sx + br_sx * 0.5 - offset);
    double ny = FTy - (floor(FTy / br_sy) * br_sy + br_sy * 0.5);
    FPx += VVAR * nx;
    FPy += VVAR * ny;
    
    return TRUE;
}
