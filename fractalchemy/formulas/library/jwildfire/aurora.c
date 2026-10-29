/*
    Fractalchemy formula library — translated from the JWildfire variation
        AuroraFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double aurora_freq;
    double aurora_amp;
    double aurora_width;
    double aurora_lat;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("aurora");

APO_VARIABLES(
    VAR_REAL(aurora_freq, 4),
    VAR_REAL(aurora_amp, 0.5),
    VAR_REAL(aurora_width, 0.3),
    VAR_REAL(aurora_lat, 0.3)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double au_width = max(fabs(VAR(aurora_width)), 0.01);
    double au_r = sqrt(FTx * FTx + FTy * FTy);
    double au_theta = atan2(FTy, FTx);
    double au_ov = 1.0 + VAR(aurora_lat) * cos(au_theta);
    double au_band = au_r - au_ov;
    double au_env = exp(- au_band * au_band / (au_width * au_width));
    double au_wave = VAR(aurora_amp) * sin(VAR(aurora_freq) * au_theta) * au_env;
    FPx += VVAR * (FTx + au_wave * cos(au_theta));
    FPy += VVAR * (FTy + au_wave * sin(au_theta));
    
    return TRUE;
}
