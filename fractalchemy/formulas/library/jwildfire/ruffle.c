/*
    Fractalchemy formula library — translated from the JWildfire variation
        RuffleFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double ruffle_freq;
    double ruffle_amp;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("ruffle");

APO_VARIABLES(
    VAR_REAL(ruffle_freq, 3),
    VAR_REAL(ruffle_amp, 0.3)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double freqa = max(fabs(VAR(ruffle_freq)), 0.01);
    double cell = floor(FTx * freqa);
    double lx = FTx * freqa - cell;
    double dir = (cell - 2.0 * floor(cell / 2.0) > 0.5) ? 1.0 : - 1.0;
    double wave = VAR(ruffle_amp) * sin(M_PI * lx) * dir;
    FPx = VVAR * FTx;
    FPy = VVAR * (FTy + wave);
    
    return TRUE;
}
