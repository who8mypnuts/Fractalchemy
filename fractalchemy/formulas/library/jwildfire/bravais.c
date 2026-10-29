/*
    Fractalchemy formula library — translated from the JWildfire variation
        BravaisFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double bravais_scale;
    double bravais_pull;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("bravais");

APO_VARIABLES(
    VAR_REAL(bravais_scale, 3),
    VAR_REAL(bravais_pull, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double bv_cx = round(FTx * VAR(bravais_scale)) / VAR(bravais_scale);
    double bv_cy = round(FTy * VAR(bravais_scale)) / VAR(bravais_scale);
    double bv_dx = bv_cx - FTx;
    double bv_dy = bv_cy - FTy;
    FPx += VVAR * (FTx + VAR(bravais_pull) * bv_dx);
    FPy += VVAR * (FTy + VAR(bravais_pull) * bv_dy);
    
    return TRUE;
}
