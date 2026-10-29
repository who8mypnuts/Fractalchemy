/*
    Fractalchemy formula library — translated from the JWildfire variation
        Inverted_JuliaFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double inverted_julia_power;
    double inverted_julia_y2_mult;
    double inverted_julia_a2x_mult;
    double inverted_julia_a2y_mult;
    double inverted_julia_a2y_add;
    double inverted_julia_cos_mult;
    double inverted_julia_y_mult;
    double inverted_julia_center;
    double inverted_julia_x2y2_add;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("inverted_julia");

APO_VARIABLES(
    VAR_REAL(inverted_julia_power, 0.25),
    VAR_REAL(inverted_julia_y2_mult, 1),
    VAR_REAL(inverted_julia_a2x_mult, 1),
    VAR_REAL(inverted_julia_a2y_mult, 1),
    VAR_REAL(inverted_julia_a2y_add, 0),
    VAR_REAL(inverted_julia_cos_mult, 0),
    VAR_REAL(inverted_julia_y_mult, 1),
    VAR_REAL(inverted_julia_center, 3.14),
    VAR_REAL(inverted_julia_x2y2_add, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double x = FTx;
    double y = FTy;
    double xs = x * x;
    double ys = y * y;
    double z = pow(xs + (ys * VAR(inverted_julia_y2_mult)), VAR(inverted_julia_power)) + VAR(inverted_julia_x2y2_add);
    double q = atan2(x * VAR(inverted_julia_a2x_mult), y * VAR(inverted_julia_a2y_mult) + VAR(inverted_julia_a2y_add)) * 0.5 + M_PI * (int)(2 * random01());
    FPx += VVAR * cos(z * VAR(inverted_julia_cos_mult)) * (sin(q) / z / VAR(inverted_julia_center));
    FPy += VVAR * cos(z * VAR(inverted_julia_cos_mult)) * (cos(q) / z / VAR(inverted_julia_center)) * VAR(inverted_julia_y_mult);
    
    return TRUE;
}
