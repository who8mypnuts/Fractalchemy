/*
    Fractalchemy formula library — translated from the JWildfire variation
        ColorWheelFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double color_wheel_sectors;
    double color_wheel_speed;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("color_wheel");

APO_VARIABLES(
    VAR_REAL(color_wheel_sectors, 6),
    VAR_REAL(color_wheel_speed, 0.3)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double r2 = FTx * FTx + FTy * FTy;
    double cw_r = sqrt(r2 + 1.0e-10);
    double cw_theta = atan2(FTy, FTx);
    double cw_new_theta = cw_theta + VAR(color_wheel_speed) * sin(VAR(color_wheel_sectors) * cw_theta);
    FPx += VVAR * cw_r * cos(cw_new_theta);
    FPy += VVAR * cw_r * sin(cw_new_theta);
    
    return TRUE;
}
