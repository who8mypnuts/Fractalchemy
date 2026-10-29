/*
    Fractalchemy formula library — translated from the JWildfire variation
        Elliptic2Func.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double elliptic2_a1;
    double elliptic2_a2;
    double elliptic2_a3;
    double elliptic2_b1;
    double elliptic2_b2;
    double elliptic2_c;
    double elliptic2_d;
    double elliptic2_e;
    double elliptic2_f;
    double elliptic2_g;
    double elliptic2_h;
    double elliptic2__v;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("elliptic2");

APO_VARIABLES(
    VAR_REAL(elliptic2_a1, 1),
    VAR_REAL(elliptic2_a2, 1),
    VAR_REAL(elliptic2_a3, 0),
    VAR_REAL(elliptic2_b1, 2),
    VAR_REAL(elliptic2_b2, 1),
    VAR_REAL(elliptic2_c, 0.5),
    VAR_REAL(elliptic2_d, 1),
    VAR_REAL(elliptic2_e, 0.5),
    VAR_REAL(elliptic2_f, 1),
    VAR_REAL(elliptic2_g, 1),
    VAR_REAL(elliptic2_h, 2)
);

double sqrt_safe(double x)
{
    return(x < EPS) ? 0.0 : sqrt(x);
}

int PluginVarPrepare(Variation* vp)
{
    VAR(elliptic2__v) = VVAR / (M_PI / VAR(elliptic2_h));
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double tmp = FTy * FTy + FTx * FTx + VAR(elliptic2_a1);
    double x2 = VAR(elliptic2_b1) * FTx;
    double xmax = VAR(elliptic2_c) * (sqrt(tmp + x2) + sqrt(tmp - x2));
    double a = FTx / xmax * VAR(elliptic2_a2);
    double b = sqrt_safe(VAR(elliptic2_d) - a * a) * VAR(elliptic2_b2);
    double ps = - M_PI_2 * VAR(elliptic2_a3);
    FPx += VAR(elliptic2__v) * atan2(a, b) + ps;
    if(random01() < VAR(elliptic2_e)) FPy += VAR(elliptic2__v) * log(xmax + sqrt_safe(xmax - VAR(elliptic2_f)));
    else FPy -= VAR(elliptic2__v) * log(xmax + sqrt_safe(xmax - VAR(elliptic2_g)));
    
    return TRUE;
}
