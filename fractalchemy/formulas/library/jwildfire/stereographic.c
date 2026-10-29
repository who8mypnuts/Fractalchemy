/*
    Fractalchemy formula library — translated from the JWildfire variation
        StereographicFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double stereographic_scale;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("stereographic");

APO_VARIABLES(
    VAR_REAL(stereographic_scale, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double st_r2 = FTx * FTx + FTy * FTy;
    double st_d = 1.0 + st_r2 * VAR(stereographic_scale);
    FPx += VVAR * 2.0 * FTx / st_d;
    FPy += VVAR * 2.0 * FTy / st_d;
    
    return TRUE;
}
