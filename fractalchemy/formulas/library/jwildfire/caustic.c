/*
    Fractalchemy formula library — translated from the JWildfire variation
        CausticFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double caustic_freq;
    double caustic_strength;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("caustic");

APO_VARIABLES(
    VAR_REAL(caustic_freq, 5),
    VAR_REAL(caustic_strength, 0.3)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double ca_r = sqrt(FTx * FTx + FTy * FTy);
    double ca_theta = atan2(FTy, FTx);
    double ca_new_r = ca_r + VAR(caustic_strength) * sin(ca_r * VAR(caustic_freq));
    FPx += VVAR * ca_new_r * cos(ca_theta);
    FPy += VVAR * ca_new_r * sin(ca_theta);
    
    return TRUE;
}
