/*
    Fractalchemy formula library — translated from the JWildfire variation
        VogelFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double vogel_M_PHI;
    double vogel_M_2PI_PHI2;
    int vogel_n;
    double vogel_scale;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("vogel");

APO_VARIABLES(
    VAR_INTEGER(vogel_n, 20),
    VAR_REAL(vogel_scale, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double sina;
    double cosa;
    int i = (int)(random01() *  VAR(vogel_n)) + 1;
    double a = i * VAR(vogel_M_2PI_PHI2);
    fsincos(a, & sina, & cosa);
    double r = VVAR * ((sqrt(FTx * FTx + FTy * FTy) + EPS) + sqrt(i));
    FPx += r * (cosa + (VAR(vogel_scale) * FTx));
    FPy += r * (sina + (VAR(vogel_scale) * FTy));
    
    return TRUE;
}
