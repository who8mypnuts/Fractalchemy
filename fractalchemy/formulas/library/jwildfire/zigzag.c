/*
    Fractalchemy formula library — translated from the JWildfire variation
        ZigzagFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double zigzag_period;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("zigzag");

APO_VARIABLES(
    VAR_REAL(zigzag_period, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double zz_period = max(fabs(VAR(zigzag_period)), 0.01);
    double zz_row = floor(FTy / zz_period);
    double row_mod = zz_row % 2.0;
    if(row_mod < 0.0) row_mod += 2.0;
    double zz_lx = (row_mod > 0.5) ? - FTx : FTx;
    FPx += VVAR * zz_lx;
    FPy += VVAR * FTy;
    
    return TRUE;
}
