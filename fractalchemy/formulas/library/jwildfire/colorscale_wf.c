/*
    Fractalchemy formula library — translated from the JWildfire variation
        ColorScaleWFFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double colorscale_wf_scale_x;
    double colorscale_wf_scale_y;
    double colorscale_wf_scale_z;
    double colorscale_wf_offset_z;
    double colorscale_wf_reset_z;
    double colorscale_wf_sides;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("colorscale_wf");

APO_VARIABLES(
    VAR_REAL(colorscale_wf_scale_x, 0),
    VAR_REAL(colorscale_wf_scale_y, 0),
    VAR_REAL(colorscale_wf_scale_z, 0.5),
    VAR_REAL(colorscale_wf_offset_z, 0),
    VAR_REAL(colorscale_wf_reset_z, 0),
    VAR_REAL(colorscale_wf_sides, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    FPx += VVAR * VAR(colorscale_wf_scale_x) * FTx;
    FPy += VVAR * VAR(colorscale_wf_scale_y) * FTy;
    double dz = TC * VAR(colorscale_wf_scale_z) * VVAR + VAR(colorscale_wf_offset_z);
    if(VAR(colorscale_wf_reset_z) > 0) {
        FPz = dz;
    } else {
        if(VAR(colorscale_wf_sides) > 0) {
            FPz += dz * random01();
        } else {
            FPz += dz;
        }
    }
    return TRUE;
}
