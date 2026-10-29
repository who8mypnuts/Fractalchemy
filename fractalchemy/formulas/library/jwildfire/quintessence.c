/*
    Fractalchemy formula library — translated from the JWildfire variation
        QuintessenceFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double quintessence_scale;
    double quintessence_power;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("quintessence");

APO_VARIABLES(
    VAR_REAL(quintessence_scale, 1),
    VAR_REAL(quintessence_power, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double qe_r2 = FTx * FTx + FTy * FTy;
    double qe_r = pow(qe_r2 + 1e-10, VAR(quintessence_power) * 0.5);
    double qe_a = atan2(FTy, FTx) * 5.0;
    FPx += VVAR * qe_r * cos(qe_a) * VAR(quintessence_scale);
    FPy += VVAR * qe_r * sin(qe_a) * VAR(quintessence_scale);
    
    return TRUE;
}
