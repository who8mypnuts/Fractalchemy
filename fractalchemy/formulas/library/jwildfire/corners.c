/*
    Fractalchemy formula library — translated from the JWildfire variation
        CornersFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double corners_x;
    double corners_y;
    double corners_mult_x;
    double corners_mult_y;
    double corners_x_power;
    double corners_y_power;
    double corners_xy_power_add;
    double corners_log_mode;
    double corners_log_base;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("corners");

APO_VARIABLES(
    VAR_REAL(corners_x, 1),
    VAR_REAL(corners_y, 1),
    VAR_REAL(corners_mult_x, 1),
    VAR_REAL(corners_mult_y, 1),
    VAR_REAL(corners_x_power, 0.75),
    VAR_REAL(corners_y_power, 0.75),
    VAR_REAL(corners_xy_power_add, 0),
    VAR_REAL(corners_log_mode, 0),
    VAR_REAL(corners_log_base, 2.71828)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double xs = FTx * FTx;
    double ys = FTy * FTy;
    double ex, ey;
    if(VAR(corners_log_mode) == 0) {
        ex = pow(xs, VAR(corners_x_power) + VAR(corners_xy_power_add)) * VAR(corners_mult_x);
        ey = pow(ys, VAR(corners_y_power) + VAR(corners_xy_power_add)) * VAR(corners_mult_y);
    } else {
        ex = pow(log((xs * VAR(corners_mult_x)) + 3) / log(VAR(corners_log_base)), VAR(corners_x_power) + 2.25 + VAR(corners_xy_power_add)) - 1.33;
        ey = pow(log((ys * VAR(corners_mult_y)) + 3) / log(VAR(corners_log_base)), VAR(corners_y_power) + 2.25 + VAR(corners_xy_power_add)) - 1.33;
    }
    if(FTx > 0) {
        FPx += VVAR * ex + VAR(corners_x);
    } else {
        FPx += VVAR * - ex - VAR(corners_x);
    }
    if(FTy > 0) {
        FPy += VVAR * ey + VAR(corners_y);
    } else {
        FPy += VVAR * - ey - VAR(corners_y);
    }
    
    return TRUE;
}
