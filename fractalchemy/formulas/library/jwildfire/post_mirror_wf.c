/*
    Fractalchemy formula library — translated from the JWildfire variation
        PostMirrorWFFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    int post_mirror_wf_xaxis;
    int post_mirror_wf_yaxis;
    int post_mirror_wf_zaxis;
    double post_mirror_wf_xshift;
    double post_mirror_wf_yshift;
    double post_mirror_wf_zshift;
    double post_mirror_wf_xscale;
    double post_mirror_wf_yscale;
    double post_mirror_wf_xcolorshift;
    double post_mirror_wf_ycolorshift;
    double post_mirror_wf_zcolorshift;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("post_mirror_wf");

APO_VARIABLES(
    VAR_INTEGER(post_mirror_wf_xaxis, 1),
    VAR_INTEGER(post_mirror_wf_yaxis, 0),
    VAR_INTEGER(post_mirror_wf_zaxis, 0),
    VAR_REAL(post_mirror_wf_xshift, 0),
    VAR_REAL(post_mirror_wf_yshift, 0),
    VAR_REAL(post_mirror_wf_zshift, 0),
    VAR_REAL(post_mirror_wf_xscale, 1),
    VAR_REAL(post_mirror_wf_yscale, 1),
    VAR_REAL(post_mirror_wf_xcolorshift, 0),
    VAR_REAL(post_mirror_wf_ycolorshift, 0),
    VAR_REAL(post_mirror_wf_zcolorshift, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    if(fabs(VVAR) > 1.0e-8) {
        if(VAR(post_mirror_wf_xaxis) > 0 && random01() < 0.5) {
            FPx = VAR(post_mirror_wf_xscale) * (- FPx - VAR(post_mirror_wf_xshift));
            FPy = VAR(post_mirror_wf_yscale) * FPy;
            TC = fmod(TC + VAR(post_mirror_wf_xcolorshift), 1.0);
        }
        if(VAR(post_mirror_wf_yaxis) > 0 && random01() < 0.5) {
            FPx = VAR(post_mirror_wf_xscale) * FPx;
            FPy = VAR(post_mirror_wf_yscale) * (- FPy - VAR(post_mirror_wf_yshift));
            TC = fmod(TC + VAR(post_mirror_wf_ycolorshift), 1.0);
        }
        if(VAR(post_mirror_wf_zaxis) > 0 && random01() < 0.5) {
            FPz = - FPz - VAR(post_mirror_wf_zshift);
            TC = fmod(TC + VAR(post_mirror_wf_zcolorshift), 1.0);
        }
    }
    return TRUE;
}
