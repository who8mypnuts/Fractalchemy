/*
    Fractalchemy formula library — translated from the JWildfire variation
        RewindFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double rewind_speed;
    double rewind_radius;
    double rewind_decay;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("rewind");

APO_VARIABLES(
    VAR_REAL(rewind_speed, 1),
    VAR_REAL(rewind_radius, 0.5),
    VAR_REAL(rewind_decay, 0.3)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double r2 = FTx * FTx + FTy * FTy;
    double rew_r = sqrt(r2 + 1.0e-10);
    double rew_theta = atan2(FTy, FTx);
    double rew_turn = VAR(rewind_speed) / (rew_r + VAR(rewind_radius));
    double rew_nr = rew_r * (1.0 - VAR(rewind_decay) * 0.05);
    double rew_nt = rew_theta + rew_turn;
    FPx += VVAR * rew_nr * cos(rew_nt);
    FPy += VVAR * rew_nr * sin(rew_nt);
    
    return TRUE;
}
