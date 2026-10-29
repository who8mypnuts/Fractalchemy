/*
    Fractalchemy formula library — translated from the JWildfire variation
        EpispiralWFFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double epispiral_wf_waves;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("epispiral_wf");

APO_VARIABLES(
    VAR_REAL(epispiral_wf_waves, 4)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double a = atan2(FTx, FTy);
    double r = sqrt(FTx * FTx + FTy * FTy);
    double d = cos(VAR(epispiral_wf_waves) * a);
    if(d == 0) {
        return;
    }
    r = 0.5 / d;
    double nx = sin(a) * r;
    double ny = cos(a) * r;
    FPx += VVAR * nx;
    FPy += VVAR * ny;
    
    return TRUE;
}
