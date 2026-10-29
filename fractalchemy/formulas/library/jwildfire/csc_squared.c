/*
    Fractalchemy formula library — translated from the JWildfire variation
        CscSquaredFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double csc_squared_csc_div;
    double csc_squared_cos_div;
    double csc_squared_tan_div;
    double csc_squared_csc_pow;
    double csc_squared_pi_mult;
    double csc_squared_csc_add;
    double csc_squared_scale_y;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("csc_squared");

APO_VARIABLES(
    VAR_REAL(csc_squared_csc_div, 1),
    VAR_REAL(csc_squared_cos_div, 1),
    VAR_REAL(csc_squared_tan_div, 1),
    VAR_REAL(csc_squared_csc_pow, 0.5),
    VAR_REAL(csc_squared_pi_mult, 0.5),
    VAR_REAL(csc_squared_csc_add, 0.25),
    VAR_REAL(csc_squared_scale_y, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double x = FTx;
    double y = FTy;
    double csc = VAR(csc_squared_csc_div) / cos(x / VAR(csc_squared_cos_div)) / tan(x / VAR(csc_squared_tan_div));
    double fx = pow(csc * csc + (M_PI * VAR(csc_squared_pi_mult)), VAR(csc_squared_csc_pow)) + VAR(csc_squared_csc_add);
    FPx += VVAR * x * fx;
    FPy += VVAR * y * fx * VAR(csc_squared_scale_y);
    
    return TRUE;
}
