/*
    Fractalchemy formula library — translated from the JWildfire variation
        AmoebaFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double amoeba_lobes;
    double amoeba_amp;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("amoeba");

APO_VARIABLES(
    VAR_REAL(amoeba_lobes, 4),
    VAR_REAL(amoeba_amp, 0.3)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double am_n = max(fabs(VAR(amoeba_lobes)), 2.0);
    double am_r = sqrt(FTx * FTx + FTy * FTy);
    double am_theta = atan2(FTy, FTx);
    double am_new_r = am_r * (1.0 + VAR(amoeba_amp) * cos(am_n * am_theta) + 0.4 * VAR(amoeba_amp) * sin((am_n + 1.0) * am_theta + 0.5));
    FPx += VVAR * am_new_r * cos(am_theta);
    FPy += VVAR * am_new_r * sin(am_theta);
    
    return TRUE;
}
