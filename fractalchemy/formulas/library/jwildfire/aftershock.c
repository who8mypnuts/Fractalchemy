/*
    Fractalchemy formula library — translated from the JWildfire variation
        AfterShockFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double aftershock_freq;
    double aftershock_amp;
    double aftershock_decay;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("aftershock");

APO_VARIABLES(
    VAR_REAL(aftershock_freq, 5),
    VAR_REAL(aftershock_amp, 0.3),
    VAR_REAL(aftershock_decay, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double as_decay = max(fabs(VAR(aftershock_decay)), 0.01);
    double as_r = sqrt(FTx * FTx + FTy * FTy);
    double as_theta = atan2(FTy, FTx);
    double as_ring = VAR(aftershock_amp) * sin(VAR(aftershock_freq) * as_r) * exp(- as_decay * as_r);
    double as_new_r = as_r + as_ring;
    FPx += VVAR * as_new_r * cos(as_theta);
    FPy += VVAR * as_new_r * sin(as_theta);
    
    return TRUE;
}
