/*
    Fractalchemy formula library — translated from the JWildfire variation
        CloverLeafWFFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double cloverleaf_wf_filled;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("cloverleaf_wf");

APO_VARIABLES(
    VAR_REAL(cloverleaf_wf_filled, 0.85)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double a = atan2(FTx, FTy);
    double r = (sin(2 * a) + 0.25 * sin(6 * a));
    if(VAR(cloverleaf_wf_filled) > 0 && VAR(cloverleaf_wf_filled) > random01()) {
        r *= random01();
    }
    double nx = sin(a) * r;
    double ny = cos(a) * r;
    FPx += VVAR * nx;
    FPy += VVAR * ny;
    
    return TRUE;
}
