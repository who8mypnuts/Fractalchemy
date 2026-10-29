/*
    Fractalchemy formula library — translated from the JWildfire variation
        CirrusFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double cirrus_freq;
    double cirrus_amp;
    double cirrus_angle;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("cirrus");

APO_VARIABLES(
    VAR_REAL(cirrus_freq, 3),
    VAR_REAL(cirrus_amp, 0.3),
    VAR_REAL(cirrus_angle, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double ci_ca = cos(VAR(cirrus_angle));
    double ci_sa = sin(VAR(cirrus_angle));
    double ci_u = FTx * ci_ca + FTy * ci_sa;
    double ci_v = - FTx * ci_sa + FTy * ci_ca;
    double ci_wisp = VAR(cirrus_amp) * (sin(VAR(cirrus_freq) * ci_u) + 0.5 * sin(VAR(cirrus_freq) * 2.3 * ci_u + 0.7));
    double ci_nv = ci_v + ci_wisp;
    FPx += VVAR * (ci_u * ci_ca - ci_nv * ci_sa);
    FPy += VVAR * (ci_u * ci_sa + ci_nv * ci_ca);
    
    return TRUE;
}
