/*
    Fractalchemy formula library — translated from the JWildfire variation
        PostColorScaleWFFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double post_colorscale_wf_scale_x;
    double post_colorscale_wf_scale_y;
    double post_colorscale_wf_scale_z;
    double post_colorscale_wf_offset_z;
    double post_colorscale_wf_reset_z;
    double post_colorscale_wf_sides;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("post_colorscale_wf");

APO_VARIABLES(
    VAR_REAL(post_colorscale_wf_scale_x, 0),
    VAR_REAL(post_colorscale_wf_scale_y, 0),
    VAR_REAL(post_colorscale_wf_scale_z, 0.5),
    VAR_REAL(post_colorscale_wf_offset_z, 0),
    VAR_REAL(post_colorscale_wf_reset_z, 0),
    VAR_REAL(post_colorscale_wf_sides, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    FPx += VVAR * VAR(post_colorscale_wf_scale_x) * FPx;
    FPy += VVAR * VAR(post_colorscale_wf_scale_y) * FPy;
    double dz = TC * VAR(post_colorscale_wf_scale_z) * VVAR + VAR(post_colorscale_wf_offset_z);
    if(VAR(post_colorscale_wf_reset_z) > 0) {
        FPz = dz;
    } else {
        if(VAR(post_colorscale_wf_sides) > 0) {
            FPz += dz * random01();
        } else {
            FPz += dz;
        }
    }
    return TRUE;
}
