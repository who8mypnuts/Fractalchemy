/*
    Fractalchemy formula library — translated from the JWildfire variation
        SchwarzChristoffelFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double schwarz_christoffel_scale;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("schwarz_christoffel");

APO_VARIABLES(
    VAR_REAL(schwarz_christoffel_scale, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double sc_s = max(fabs(VAR(schwarz_christoffel_scale)), 0.01);
    double sc_ex = exp(M_PI * FTx / sc_s);
    FPx += VVAR * sc_ex * cos(M_PI * FTy / sc_s);
    FPy += VVAR * sc_ex * sin(M_PI * FTy / sc_s);
    
    return TRUE;
}
