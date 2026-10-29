/*
    Fractalchemy formula library — translated from the JWildfire variation
        JetStreamFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double jet_stream_speed;
    double jet_stream_width;
    double jet_stream_center;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("jet_stream");

APO_VARIABLES(
    VAR_REAL(jet_stream_speed, 1),
    VAR_REAL(jet_stream_width, 0.3),
    VAR_REAL(jet_stream_center, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double js_width = max(fabs(VAR(jet_stream_width)), 0.01);
    double js_dy = FTy - VAR(jet_stream_center);
    double js_profile = exp(- (js_dy * js_dy) / (js_width * js_width));
    FPx += VVAR * (FTx + VAR(jet_stream_speed) * js_profile);
    FPy += VVAR * FTy;
    
    return TRUE;
}
