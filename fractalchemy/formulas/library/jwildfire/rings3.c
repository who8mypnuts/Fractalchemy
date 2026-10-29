/*
    Fractalchemy formula library — translated from the JWildfire variation
        Rings3Func.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double rings3_val;
    double rings3_n;
    double rings3__dx;
    double rings3_c;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("rings3");

APO_VARIABLES(
    VAR_REAL(rings3_val, 0.01),
    VAR_REAL(rings3_n, 0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(rings3__dx) = VAR(rings3_val) * VAR(rings3_val) + 1.0e-8;
    VAR(rings3_c) = 2.0 * (VAR(rings3__dx) - VAR(rings3__dx) * VAR(rings3__dx));
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double l = (sqrt(FTx * FTx + FTy * FTy) + EPS);
    if(VAR(rings3__dx) == 0 || l == 0) {
        return;
    }
    double k = (int)(l / VAR(rings3__dx) + 1) / 2;
    double r = VVAR * (2.0 - VAR(rings3__dx) * (k * 2 / l + 1) - VAR(rings3_n) * (k * VAR(rings3_c) - 1) / l);
    FPx += r * FTx;
    FPy += r * FTy;
    
    return TRUE;
}
