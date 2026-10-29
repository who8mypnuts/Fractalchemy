/*
    Fractalchemy formula library — translated from the JWildfire variation
        SupernovaFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double supernova_radius;
    double supernova_boost;
    double supernova_spin;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("supernova");

APO_VARIABLES(
    VAR_REAL(supernova_radius, 0.5),
    VAR_REAL(supernova_boost, 2),
    VAR_REAL(supernova_spin, 0.3)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double sn_radius = max(fabs(VAR(supernova_radius)), 0.01);
    double sn_r = sqrt(FTx * FTx + FTy * FTy);
    double sn_theta = atan2(FTy, FTx);
    double sn_ring = sn_r - sn_radius;
    double sn_env = exp(- sn_ring * sn_ring / (sn_radius * sn_radius * 0.1 + 1e-6));
    double sn_new_r = sn_r + sn_env * VAR(supernova_boost) * sn_r;
    double sn_new_theta = sn_theta + VAR(supernova_spin) * sn_env;
    FPx += VVAR * sn_new_r * cos(sn_new_theta);
    FPy += VVAR * sn_new_r * sin(sn_new_theta);
    
    return TRUE;
}
