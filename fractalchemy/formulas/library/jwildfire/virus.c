/*
    Fractalchemy formula library — translated from the JWildfire variation
        VirusFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double virus_spread;
    double virus_mut;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("virus");

APO_VARIABLES(
    VAR_REAL(virus_spread, 2),
    VAR_REAL(virus_mut, 0.3)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double vr_s = sin(FTx * VAR(virus_spread)) * cos(FTy * VAR(virus_spread));
    double sign_x = (FTx == 0.0) ? 0.0 : ((FTx < 0.0) ? - 1.0 : 1.0);
    double sign_y = (FTy == 0.0) ? 0.0 : ((FTy < 0.0) ? - 1.0 : 1.0);
    double vr_nx = FTx + VAR(virus_mut) * vr_s * sign_x;
    double vr_ny = FTy - VAR(virus_mut) * vr_s * sign_y;
    double vr_r = sqrt(FTx * FTx + FTy * FTy);
    double vr_nr = sqrt(vr_nx * vr_nx + vr_ny * vr_ny);
    double vr_scale = vr_r / (vr_nr + 1e-6);
    FPx += VVAR * vr_nx * vr_scale;
    FPy += VVAR * vr_ny * vr_scale;
    
    return TRUE;
}
