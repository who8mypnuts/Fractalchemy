/*
    Fractalchemy formula library — translated from the JWildfire variation
        CamFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double cam_k1;
    double cam_k2;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("cam");

APO_VARIABLES(
    VAR_REAL(cam_k1, 0.5),
    VAR_REAL(cam_k2, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double cam_r2 = FTx * FTx + FTy * FTy;
    double cam_d = 1.0 + VAR(cam_k1) * cam_r2 + VAR(cam_k2) * cam_r2 * cam_r2;
    FPx += VVAR * FTx * cam_d;
    FPy += VVAR * FTy * cam_d;
    
    return TRUE;
}
