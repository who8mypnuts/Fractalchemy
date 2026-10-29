/*
    Fractalchemy formula library — translated from the JWildfire variation
        HaloFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double halo_radius;
    double halo_width;
    double halo_strength;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("halo");

APO_VARIABLES(
    VAR_REAL(halo_radius, 0.5),
    VAR_REAL(halo_width, 0.2),
    VAR_REAL(halo_strength, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double hl_rad = max(fabs(VAR(halo_radius)), 0.01);
    double hl_w = max(fabs(VAR(halo_width)), 0.01);
    double hl_r = sqrt(FTx * FTx + FTy * FTy);
    double hl_ring = hl_r - hl_rad;
    double hl_env = exp(- (hl_ring * hl_ring) / (hl_w * hl_w));
    double hl_scale = 1.0 + VAR(halo_strength) * hl_env / (hl_r + 1e-6);
    FPx += VVAR * FTx * hl_scale;
    FPy += VVAR * FTy * hl_scale;
    
    return TRUE;
}
