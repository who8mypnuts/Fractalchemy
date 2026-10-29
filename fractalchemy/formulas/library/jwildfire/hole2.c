/*
    Fractalchemy formula library — translated from the JWildfire variation
        Hole2Func.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double hole2_a;
    double hole2_b;
    double hole2_c;
    double hole2_d;
    int hole2_inside;
    int hole2_shape;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("hole2");

APO_VARIABLES(
    VAR_REAL(hole2_a, 1),
    VAR_REAL(hole2_b, 2),
    VAR_REAL(hole2_c, 1),
    VAR_REAL(hole2_d, 1),
    VAR_INTEGER(hole2_inside, 0),
    VAR_INTEGER(hole2_shape, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double rhosq = (FTx * FTx + FTy * FTy);
    double theta = atan2(FTy, FTx) * VAR(hole2_d);
    double delta = pow(theta / M_PI + 1.0, VAR(hole2_a)) * VAR(hole2_c);
    double r1 = 1;
    switch(VAR(hole2_shape)) {
        case 0 : r1 = sqrt(rhosq) + delta;
        break;
        case 1 : r1 = sqrt(rhosq + delta);
        break;
        case 2 : r1 = sqrt(rhosq + sin(VAR(hole2_b) * theta) + delta);
        break;
        case 3 : r1 = sqrt(rhosq + sin(theta) + delta);
        break;
        case 4 : r1 = sqrt(rhosq + sqr(theta) - delta + 1);
        break;
        case 5 : r1 = sqrt(rhosq + fabs(tan(theta)) + delta);
        break;
        case 6 : r1 = sqrt(rhosq * (1 + sin(VAR(hole2_b) * theta)) + delta);
        break;
        case 7 : r1 = sqrt(rhosq + fabs(sin(0.5 * VAR(hole2_b) * theta)) + delta);
        break;
        case 8 : r1 = sqrt(rhosq + sin(M_PI * sin(VAR(hole2_b) * theta)) + delta);
        break;
        case 9 : r1 = sqrt(rhosq + (sin(VAR(hole2_b) * theta) + sin(2 * VAR(hole2_b) * theta + M_PI_2)) / 2 + delta);
        break;
    }
    if(VAR(hole2_inside) != 0) r1 = VVAR / r1;
    else r1 = VVAR * r1;
    FPx += r1 * cos(theta);
    FPy += r1 * sin(theta);
    
    return TRUE;
}
