/*
    Fractalchemy formula library — translated from the JWildfire variation
        IkedaFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double ikeda_u;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("ikeda");

APO_VARIABLES(
    VAR_REAL(ikeda_u, 0.9)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t = 0.4 - 6.0 / (1.0 + FTx * FTx + FTy * FTy);
    double cos_t = cos(t);
    double sin_t = sin(t);
    double nx = 1.0 + VAR(ikeda_u) * (FTx * cos_t - FTy * sin_t);
    double ny = VAR(ikeda_u) * (FTx * sin_t + FTy * cos_t);
    FPx += VVAR * nx;
    FPy += VVAR * ny;
    
    return TRUE;
}
