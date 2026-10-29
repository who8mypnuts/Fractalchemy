/*
    Fractalchemy formula library — translated from the JWildfire variation
        SatinFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double satin_freq;
    double satin_sheen;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("satin");

APO_VARIABLES(
    VAR_REAL(satin_freq, 4),
    VAR_REAL(satin_sheen, 0.2)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double sa_freq = max(fabs(VAR(satin_freq)), 0.01);
    double sa_diag1 = (FTx + FTy) * 0.7071067811865476;
    double sa_diag2 = (FTx - FTy) * 0.7071067811865476;
    double sa_dx = VAR(satin_sheen) * sin(sa_freq * sa_diag1);
    double sa_dy = VAR(satin_sheen) * cos(sa_freq * sa_diag2);
    FPx += VVAR * (FTx + sa_dx);
    FPy += VVAR * (FTy + sa_dy);
    
    return TRUE;
}
