/*
    Fractalchemy formula library — translated from the JWildfire variation
        SplipticBSFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double spliptic_bs_x;
    double spliptic_bs_y;
    double spliptic_bs__v;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("spliptic_bs");

APO_VARIABLES(
    VAR_REAL(spliptic_bs_x, 0.05),
    VAR_REAL(spliptic_bs_y, 0.05)
);

double sqrt_safe(double x)
{
    return(x < EPS) ? 0.0 : sqrt(x);
}

int PluginVarPrepare(Variation* vp)
{
    VAR(spliptic_bs__v) = VVAR / (M_PI / 2.0);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double tmp = FTy * FTy + FTx * FTx + 1.0;
    double x2 = 2.0 * FTx;
    double xmax = 0.5 * (sqrt(tmp + x2) + sqrt(tmp - x2));
    double a = FTx / xmax;
    double b = sqrt_safe(1.0 - a * a);
    if(FTx >= 0) {
        FPx += VAR(spliptic_bs__v) * atan2(a, b) + VAR(spliptic_bs_x);
    } else {
        FPx += VAR(spliptic_bs__v) * atan2(a, b) - VAR(spliptic_bs_x);
    }
    if(random01() < 0.5) FPy += VAR(spliptic_bs__v) * log(xmax + sqrt_safe(xmax - 1.0)) + VAR(spliptic_bs_y);
    else FPy -= VAR(spliptic_bs__v) * log(xmax + sqrt_safe(xmax - 1.0)) + VAR(spliptic_bs_y);
    
    return TRUE;
}
