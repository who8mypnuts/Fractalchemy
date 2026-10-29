/*
    Fractalchemy formula library — translated from the JWildfire variation
        DopplerFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double doppler_dir;
    double doppler_speed;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("doppler");

APO_VARIABLES(
    VAR_REAL(doppler_dir, 0),
    VAR_REAL(doppler_speed, 0.5)
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
    double dp_spd = clamp(VAR(doppler_speed), - 0.99, 0.99);
    double dp_ca = cos(VAR(doppler_dir));
    double dp_sa = sin(VAR(doppler_dir));
    double dp_along = FTx * dp_ca + FTy * dp_sa;
    double dp_perp = - FTx * dp_sa + FTy * dp_ca;
    double dp_scale = 1.0 / (1.0 + dp_spd * dp_along);
    double dp_r = dp_along * dp_scale;
    FPx += VVAR * (dp_r * dp_ca - dp_perp * dp_sa);
    FPy += VVAR * (dp_r * dp_sa + dp_perp * dp_ca);
    
    return TRUE;
}
