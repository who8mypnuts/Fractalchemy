/*
    Fractalchemy formula library — translated from the JWildfire variation
        Waves2WFFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double waves2_wf_scalex;
    double waves2_wf_scaley;
    double waves2_wf_freqx;
    double waves2_wf_freqy;
    int waves2_wf_use_cos_x;
    int waves2_wf_use_cos_y;
    double waves2_wf_dampx;
    double waves2_wf_dampy;
    double waves2_wf__dampingX;
    double waves2_wf__dampingY;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("waves2_wf");

APO_VARIABLES(
    VAR_REAL(waves2_wf_scalex, 0.25),
    VAR_REAL(waves2_wf_scaley, 0.5),
    VAR_REAL(waves2_wf_freqx, 1.5708),
    VAR_REAL(waves2_wf_freqy, 0.785398),
    VAR_INTEGER(waves2_wf_use_cos_x, 1),
    VAR_INTEGER(waves2_wf_use_cos_y, 0),
    VAR_REAL(waves2_wf_dampx, 0),
    VAR_REAL(waves2_wf_dampy, 0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(waves2_wf__dampingX) = fabs(VAR(waves2_wf_dampx)) < 1.0e-8 ? 1.0 : exp(VAR(waves2_wf_dampx));
    VAR(waves2_wf__dampingY) = fabs(VAR(waves2_wf_dampy)) < 1.0e-8 ? 1.0 : exp(VAR(waves2_wf_dampy));
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    if(VAR(waves2_wf_use_cos_x) == 1) {
        FPx += VVAR * (FTx + VAR(waves2_wf__dampingX) * VAR(waves2_wf_scalex) * cos(FTy * VAR(waves2_wf_freqx))) * VAR(waves2_wf__dampingX);
    } else {
        FPx += VVAR * (FTx + VAR(waves2_wf__dampingX) * VAR(waves2_wf_scalex) * sin(FTy * VAR(waves2_wf_freqx))) * VAR(waves2_wf__dampingX);
    }
    if(VAR(waves2_wf_use_cos_y) == 1) {
        FPy += VVAR * (FTy + VAR(waves2_wf__dampingY) * VAR(waves2_wf_scaley) * cos(FTx * VAR(waves2_wf_freqy))) * VAR(waves2_wf__dampingY);
    } else {
        FPy += VVAR * (FTy + VAR(waves2_wf__dampingY) * VAR(waves2_wf_scaley) * sin(FTx * VAR(waves2_wf_freqy))) * VAR(waves2_wf__dampingY);
    }
    
    return TRUE;
}
