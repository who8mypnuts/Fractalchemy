/*
    Fractalchemy formula library — translated from the JWildfire variation
        RainbowArcFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double rainbow_arc_radius;
    double rainbow_arc_width;
    double rainbow_arc_arc;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("rainbow_arc");

APO_VARIABLES(
    VAR_REAL(rainbow_arc_radius, 0.5),
    VAR_REAL(rainbow_arc_width, 0.2),
    VAR_REAL(rainbow_arc_arc, 3.14159)
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
    double ra_radius = max(fabs(VAR(rainbow_arc_radius)), 0.01);
    double ra_width = max(fabs(VAR(rainbow_arc_width)), 0.001);
    double ra_arc = max(fabs(VAR(rainbow_arc_arc)), 0.01);
    double ra_r = sqrt(FTx * FTx + FTy * FTy);
    double ra_theta = atan2(FTy, FTx);
    double ra_band_r = round((ra_r - ra_radius) / ra_width) * ra_width + ra_radius;
    double ra_new_r = ra_r + 0.6 * (max(ra_band_r, 1e-4) - ra_r);
    double ra_new_theta = clamp(ra_theta, - ra_arc, ra_arc);
    FPx += VVAR * ra_new_r * cos(ra_new_theta);
    FPy += VVAR * ra_new_r * sin(ra_new_theta);
    
    return TRUE;
}
