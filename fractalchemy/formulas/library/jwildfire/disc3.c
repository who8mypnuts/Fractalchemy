/*
    Fractalchemy formula library — translated from the JWildfire variation
        Disc3Func.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double disc3_a;
    double disc3_b;
    double disc3_c;
    double disc3_d;
    double disc3_e;
    double disc3_f;
    double disc3_g;
    double disc3_h;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("disc3");

APO_VARIABLES(
    VAR_REAL(disc3_a, 1),
    VAR_REAL(disc3_b, 1),
    VAR_REAL(disc3_c, 1),
    VAR_REAL(disc3_d, 1),
    VAR_REAL(disc3_e, 1),
    VAR_REAL(disc3_f, 1),
    VAR_REAL(disc3_g, 1),
    VAR_REAL(disc3_h, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double rPI = M_PI * sqrt(FTx * VAR(disc3_d) * FTx * VAR(disc3_e) + FTy * VAR(disc3_f) * FTy * VAR(disc3_g));
    double sinr = sin(rPI) * VAR(disc3_a);
    double cosr = cos(rPI) * VAR(disc3_b);
    double r = VVAR * atan2(FTx, FTy) / M_PI * VAR(disc3_c);
    FPx += sinr * VAR(disc3_h) * r;
    FPy += cosr * VAR(disc3_h) * r;
    
    return TRUE;
}
