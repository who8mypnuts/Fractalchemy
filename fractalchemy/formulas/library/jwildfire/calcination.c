/*
    Fractalchemy formula library — translated from the JWildfire variation
        CalcinationFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double calcination_freq;
    double calcination_intensity;
    double calcination_decay;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("calcination");

APO_VARIABLES(
    VAR_REAL(calcination_freq, 4),
    VAR_REAL(calcination_intensity, 0.3),
    VAR_REAL(calcination_decay, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double cal_decay = max(fabs(VAR(calcination_decay)), 0.01);
    double cal_r = sqrt(FTx * FTx + FTy * FTy);
    double cal_theta = atan2(FTy, FTx);
    double cal_heat = VAR(calcination_intensity) * sin(VAR(calcination_freq) * cal_r) * exp(- cal_decay * cal_r);
    double cal_new_r = max(cal_r - cal_heat, 0.0);
    FPx += VVAR * cal_new_r * cos(cal_theta);
    FPy += VVAR * cal_new_r * sin(cal_theta);
    
    return TRUE;
}
