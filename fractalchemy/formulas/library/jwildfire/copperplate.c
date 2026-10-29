/*
    Fractalchemy formula library — translated from the JWildfire variation
        CopperplateFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double copperplate_angle;
    double copperplate_freq;
    double copperplate_width;
    double copperplate_taper;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("copperplate");

APO_VARIABLES(
    VAR_REAL(copperplate_angle, 0),
    VAR_REAL(copperplate_freq, 5),
    VAR_REAL(copperplate_width, 0.3),
    VAR_REAL(copperplate_taper, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double cp_ca = cos(VAR(copperplate_angle));
    double cp_sa = sin(VAR(copperplate_angle));
    double cp_u = FTx * cp_ca + FTy * cp_sa;
    double cp_v = - FTx * cp_sa + FTy * cp_ca;
    double cp_env = exp(- fabs(cp_u) * VAR(copperplate_taper));
    double cp_nv = cp_v * (1.0 + VAR(copperplate_width) * cp_env * sin(VAR(copperplate_freq) * cp_u));
    FPx += VVAR * (cp_u * cp_ca - cp_nv * cp_sa);
    FPy += VVAR * (cp_u * cp_sa + cp_nv * cp_ca);
    
    return TRUE;
}
