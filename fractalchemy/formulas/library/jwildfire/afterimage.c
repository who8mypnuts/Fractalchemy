/*
    Fractalchemy formula library — translated from the JWildfire variation
        AfterimageFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double afterimage_freq;
    double afterimage_len;
    double afterimage_decay;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("afterimage");

APO_VARIABLES(
    VAR_REAL(afterimage_freq, 3),
    VAR_REAL(afterimage_len, 0.4),
    VAR_REAL(afterimage_decay, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double ai_decay = max(fabs(VAR(afterimage_decay)), 0.01);
    double ai_smear = VAR(afterimage_len) * sin(VAR(afterimage_freq) * FTy) * exp(- FTy * FTy * ai_decay);
    FPx += VVAR * (FTx + ai_smear);
    FPy += VVAR * FTy;
    
    return TRUE;
}
