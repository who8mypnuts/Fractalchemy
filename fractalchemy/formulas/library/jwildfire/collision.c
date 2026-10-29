/*
    Fractalchemy formula library — translated from the JWildfire variation
        CollisionFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double collision_radius;
    double collision_force;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("collision");

APO_VARIABLES(
    VAR_REAL(collision_radius, 0.3),
    VAR_REAL(collision_force, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double cl_radius = max(fabs(VAR(collision_radius)), 0.01);
    double cl_r = sqrt(FTx * FTx + FTy * FTy);
    double cl_safe = max(cl_r, 0.0001);
    double cl_force_val = VAR(collision_force) * exp(- cl_r * cl_r / (cl_radius * cl_radius));
    FPx += VVAR * (FTx + cl_force_val * FTx / cl_safe);
    FPy += VVAR * (FTy + cl_force_val * FTy / cl_safe);
    
    return TRUE;
}
