/*
    Fractalchemy formula library — translated from the JWildfire variation
        CoronaFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double corona_n;
    double corona_amp;
    double corona_decay;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("corona");

APO_VARIABLES(
    VAR_REAL(corona_n, 8),
    VAR_REAL(corona_amp, 0.5),
    VAR_REAL(corona_decay, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double cr_decay = max(fabs(VAR(corona_decay)), 0.01);
    double cr_r = sqrt(FTx * FTx + FTy * FTy);
    double cr_theta = atan2(FTy, FTx);
    double cr_jet = VAR(corona_amp) * exp(- cr_decay * cr_r) * fabs(cos(VAR(corona_n) * cr_theta * 0.5));
    double cr_new_r = cr_r + cr_jet;
    FPx += VVAR * cr_new_r * cos(cr_theta);
    FPy += VVAR * cr_new_r * sin(cr_theta);
    
    return TRUE;
}
