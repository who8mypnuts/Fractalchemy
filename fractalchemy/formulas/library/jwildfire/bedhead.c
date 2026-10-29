/*
    Fractalchemy formula library — translated from the JWildfire variation
        BedheadFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double bedhead_a;
    double bedhead_b;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("bedhead");

APO_VARIABLES(
    VAR_REAL(bedhead_a, -0.81),
    VAR_REAL(bedhead_b, -0.92)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double b_safe = (fabs(VAR(bedhead_b)) < 0.001) ? ((VAR(bedhead_b) + 0.00001 < 0) ? - 1.0 : 1.0) * 0.001 : VAR(bedhead_b);
    double nx = sin(FTx * FTy / b_safe) * FTy + cos(VAR(bedhead_a) * FTx - FTy);
    double ny = FTx + sin(FTy) / b_safe;
    FPx += VVAR * nx;
    FPy += VVAR * ny;
    
    return TRUE;
}
