/*
    Fractalchemy formula library — translated from the JWildfire variation
        MembraneFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double membrane_radius;
    double membrane_height;
    double membrane_stiff;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("membrane");

APO_VARIABLES(
    VAR_REAL(membrane_radius, 0.5),
    VAR_REAL(membrane_height, 0.3),
    VAR_REAL(membrane_stiff, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double mb_radius = max(fabs(VAR(membrane_radius)), 0.01);
    double mb_stiff = max(fabs(VAR(membrane_stiff)), 0.01);
    double mb_r = sqrt(FTx * FTx + FTy * FTy);
    double mb_ring = mb_r - mb_radius;
    double mb_env = exp(- mb_ring * mb_ring / (mb_radius * mb_radius * mb_stiff));
    double mb_safe = max(mb_r, 0.001);
    double il_scale = (mb_r + VAR(membrane_height) * mb_env) / mb_safe;
    FPx = VVAR * FTx * il_scale;
    FPy = VVAR * FTy * il_scale;
    
    return TRUE;
}
