/*
    Fractalchemy formula library — translated from the JWildfire variation
        TurbulenceFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double turbulence_freq;
    double turbulence_amp;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("turbulence");

APO_VARIABLES(
    VAR_REAL(turbulence_freq, 2),
    VAR_REAL(turbulence_amp, 0.3)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double tb_f = VAR(turbulence_freq);
    double tb_a = VAR(turbulence_amp);
    double dx = tb_a * (sin(tb_f * FTx) * cos(tb_f * 0.7 * FTy) + 0.5 * sin(2.0 * tb_f * FTx) * cos(1.4 * tb_f * FTy));
    double dy = tb_a * (cos(0.8 * tb_f * FTx) * sin(tb_f * FTy) + 0.5 * cos(1.6 * tb_f * FTx) * sin(2.0 * tb_f * FTy));
    FPx += VVAR * (FTx + dx);
    FPy += VVAR * (FTy + dy);
    
    return TRUE;
}
