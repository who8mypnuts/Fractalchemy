/*
    Fractalchemy formula library — translated from the JWildfire variation
        PistonFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double piston_freq;
    double piston_amp;
    double piston_offset;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("piston");

APO_VARIABLES(
    VAR_REAL(piston_freq, 2),
    VAR_REAL(piston_amp, 0.5),
    VAR_REAL(piston_offset, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double ps_comp = 1.0 + VAR(piston_amp) * sin(VAR(piston_freq) * FTx + VAR(piston_offset));
    FPx += VVAR * FTx;
    FPy += VVAR * FTy * ps_comp;
    
    return TRUE;
}
