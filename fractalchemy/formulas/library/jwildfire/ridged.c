/*
    Fractalchemy formula library — translated from the JWildfire variation
        RidgedFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double ridged_freq;
    double ridged_amp;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("ridged");

APO_VARIABLES(
    VAR_REAL(ridged_freq, 2),
    VAR_REAL(ridged_amp, 0.4)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double rg_x = VAR(ridged_freq) * FTx;
    double rg_y = VAR(ridged_freq) * FTy;
    double rg_v1 = 1.0 - fabs(sin(rg_x + rg_y * 0.3));
    double rg_v2 = (1.0 - fabs(sin(2.1 * rg_x - rg_y * 0.7))) * 0.5;
    double rg_val = VAR(ridged_amp) * (rg_v1 + rg_v2);
    double rg_theta = atan2(FTy, FTx);
    FPx += VVAR * rg_val * cos(rg_theta);
    FPy += VVAR * rg_val * sin(rg_theta);
    
    return TRUE;
}
