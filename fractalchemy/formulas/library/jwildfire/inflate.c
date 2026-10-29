/*
    Fractalchemy formula library — translated from the JWildfire variation
        InflateFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double inflate_strength;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("inflate");

APO_VARIABLES(
    VAR_REAL(inflate_strength, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double il_r = sqrt(FTx * FTx + FTy * FTy);
    double il_nr = il_r + VAR(inflate_strength) * exp(- il_r);
    double il_scale = il_r > 0.001 ? il_nr / il_r : 1.0;
    FPx += VVAR * FTx * il_scale;
    FPy += VVAR * FTy * il_scale;
    
    return TRUE;
}
