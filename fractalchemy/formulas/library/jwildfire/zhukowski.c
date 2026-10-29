/*
    Fractalchemy formula library — translated from the JWildfire variation
        ZhukowskiFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double zhukowski_c;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("zhukowski");

APO_VARIABLES(
    VAR_REAL(zhukowski_c, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double zk_r2 = FTx * FTx + FTy * FTy + 1e-6;
    FPx += VVAR * (FTx + VAR(zhukowski_c) * FTx / zk_r2);
    FPy += VVAR * (FTy - VAR(zhukowski_c) * FTy / zk_r2);
    
    return TRUE;
}
