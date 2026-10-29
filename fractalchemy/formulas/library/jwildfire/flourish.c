/*
    Fractalchemy formula library — translated from the JWildfire variation
        FlourishFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double flourish_n;
    double flourish_amp;
    double flourish_damp;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("flourish");

APO_VARIABLES(
    VAR_REAL(flourish_n, 3),
    VAR_REAL(flourish_amp, 0.5),
    VAR_REAL(flourish_damp, 0.3)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double fl_damp = max(fabs(VAR(flourish_damp)), 0.01);
    double fl_r = sqrt(FTx * FTx + FTy * FTy);
    double fl_theta = atan2(FTy, FTx);
    double fl_loop = VAR(flourish_amp) * sin(VAR(flourish_n) * fl_theta) * exp(- fl_damp * fl_r);
    double fl_new_r = fl_r + fl_loop;
    FPx += VVAR * fl_new_r * cos(fl_theta);
    FPy += VVAR * fl_new_r * sin(fl_theta);
    
    return TRUE;
}
