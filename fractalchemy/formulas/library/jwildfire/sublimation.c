/*
    Fractalchemy formula library — translated from the JWildfire variation
        SublimationFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double sublimation_lift;
    double sublimation_spread;
    double sublimation_freq;
    double sublimation_amp;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("sublimation");

APO_VARIABLES(
    VAR_REAL(sublimation_lift, 0.3),
    VAR_REAL(sublimation_spread, 1),
    VAR_REAL(sublimation_freq, 3),
    VAR_REAL(sublimation_amp, 0.1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double sub_rise = exp(- fabs(FTx) * VAR(sublimation_spread)) * VAR(sublimation_lift);
    double sub_turb = VAR(sublimation_amp) * sin(VAR(sublimation_freq) * FTy);
    FPx += VVAR * (FTx + sub_turb);
    FPy += VVAR * (FTy + sub_rise);
    
    return TRUE;
}
