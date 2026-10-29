/*
    Fractalchemy formula library — translated from the JWildfire variation
        TunnelingFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double tunneling_barrier;
    double tunneling_decay;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("tunneling");

APO_VARIABLES(
    VAR_REAL(tunneling_barrier, 0.5),
    VAR_REAL(tunneling_decay, 3)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double qt_x = FTx - VAR(tunneling_barrier);
    double qt_prob = qt_x > 0.0 ? exp(- VAR(tunneling_decay) * qt_x) : 1.0;
    FPx += VVAR * FTx * qt_prob;
    FPy += VVAR * FTy * qt_prob;
    
    return TRUE;
}
