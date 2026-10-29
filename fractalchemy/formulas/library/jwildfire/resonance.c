/*
    Fractalchemy formula library — translated from the JWildfire variation
        ResonanceFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double resonance_freq;
    double resonance_decay;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("resonance");

APO_VARIABLES(
    VAR_REAL(resonance_freq, 3),
    VAR_REAL(resonance_decay, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double rs_freq = max(fabs(VAR(resonance_freq)), 0.01);
    double rs_r = sqrt(FTx * FTx + FTy * FTy);
    double rs_theta = atan2(FTy, FTx);
    double rs_ring = round(rs_r * rs_freq) / rs_freq;
    double rs_dist = rs_r - rs_ring;
    double rs_pull = VAR(resonance_decay) * exp(- rs_dist * rs_dist * rs_freq * rs_freq * 4.0);
    double rs_new_r = rs_r - rs_pull * rs_dist;
    FPx += VVAR * rs_new_r * cos(rs_theta);
    FPy += VVAR * rs_new_r * sin(rs_theta);
    
    return TRUE;
}
