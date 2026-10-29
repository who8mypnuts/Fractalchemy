/*
    Fractalchemy formula library — translated from the JWildfire variation
        FogBankFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double fog_bank_haze;
    double fog_bank_wind;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("fog_bank");

APO_VARIABLES(
    VAR_REAL(fog_bank_haze, 0.5),
    VAR_REAL(fog_bank_wind, 0.3)
);

double clamp(double value, double min, double max)
{
    return max(min, min(max, value));
}

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double fg_haze = clamp(VAR(fog_bank_haze), 0.0, 1.0);
    double fg_r2 = FTx * FTx + FTy * FTy;
    double fg_fade = 1.0 - fg_haze * exp(- fg_r2 * 0.5);
    double fg_dx = VAR(fog_bank_wind) * 0.3;
    double fg_dy = VAR(fog_bank_wind) * 0.05 * sin(FTx);
    FPx += VVAR * (FTx * fg_fade + fg_dx);
    FPy += VVAR * (FTy * fg_fade + fg_dy);
    
    return TRUE;
}
