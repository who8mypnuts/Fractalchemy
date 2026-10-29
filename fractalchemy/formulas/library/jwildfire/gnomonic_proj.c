/*
    Fractalchemy formula library — translated from the JWildfire variation
        GnomonicProjFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double gnomonic_proj_scale;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("gnomonic_proj");

APO_VARIABLES(
    VAR_REAL(gnomonic_proj_scale, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double gp_r = sqrt(FTx * FTx + FTy * FTy);
    double gp_theta = atan2(FTy, FTx);
    double gp_nr = gp_r > 0.001 ? tan(gp_r * VAR(gnomonic_proj_scale)) / VAR(gnomonic_proj_scale) : gp_r;
    FPx += VVAR * gp_nr * cos(gp_theta);
    FPy += VVAR * gp_nr * sin(gp_theta);
    
    return TRUE;
}
