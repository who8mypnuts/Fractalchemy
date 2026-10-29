/*
    Fractalchemy formula library — translated from the JWildfire variation
        LaminarFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double laminar_shear;
    double laminar_amp;
    double laminar_freq;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("laminar");

APO_VARIABLES(
    VAR_REAL(laminar_shear, 0.5),
    VAR_REAL(laminar_amp, 0.1),
    VAR_REAL(laminar_freq, 2)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double lm_flow = VAR(laminar_shear) * (1.0 - FTy * FTy);
    FPx += VVAR * (lm_flow + VAR(laminar_amp) * sin(VAR(laminar_freq) * FTy));
    FPy += VVAR * FTy;
    
    return TRUE;
}
