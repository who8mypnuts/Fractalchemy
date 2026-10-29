/*
    Fractalchemy formula library — translated from the JWildfire variation
        Disc2Func.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double disc2_rot;
    double disc2_twist;
    double disc2_timespi;
    double disc2_sinadd;
    double disc2_cosadd;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("disc2");

APO_VARIABLES(
    VAR_REAL(disc2_rot, 2),
    VAR_REAL(disc2_twist, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    double add = VAR(disc2_twist);
    VAR(disc2_timespi) = VAR(disc2_rot) * M_PI;
    VAR(disc2_sinadd) = sin(add);
    VAR(disc2_cosadd) = cos(add);
    VAR(disc2_cosadd) -= 1;
    double k;
    if(add > 2.0 * M_PI) {
        k = (1 + add - 2.0 * M_PI);
        VAR(disc2_cosadd) *= k;
        VAR(disc2_sinadd) *= k;
    }
    if(add < - 2.0 * M_PI) {
        k = (1 + add + 2.0 * M_PI);
        VAR(disc2_cosadd) *= k;
        VAR(disc2_sinadd) *= k;
    }
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t = VAR(disc2_timespi) * (FTx + FTy);
    double sinr = sin(t);
    double cosr = cos(t);
    double r = VVAR * atan2(FTx, FTy) / M_PI;
    FPx += (sinr + VAR(disc2_cosadd)) * r;
    FPy += (cosr + VAR(disc2_sinadd)) * r;
    
    return TRUE;
}
