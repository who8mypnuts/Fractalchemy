/*
    Fractalchemy formula library — translated from the JWildfire variation
        PreRectWFFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double pre_rect_wf_x0;
    double pre_rect_wf_x1;
    double pre_rect_wf_y0;
    double pre_rect_wf_y1;
    double pre_rect_wf_dx;
    double pre_rect_wf_dy;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("pre_rect_wf");

APO_VARIABLES(
    VAR_REAL(pre_rect_wf_x0, -0.5),
    VAR_REAL(pre_rect_wf_x1, 0.5),
    VAR_REAL(pre_rect_wf_y0, -0.5),
    VAR_REAL(pre_rect_wf_y1, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(pre_rect_wf_dx) = VAR(pre_rect_wf_x1) - VAR(pre_rect_wf_x0);
    VAR(pre_rect_wf_dy) = VAR(pre_rect_wf_y1) - VAR(pre_rect_wf_y0);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    FTx = VVAR * (VAR(pre_rect_wf_x0) + VAR(pre_rect_wf_dx) * random01());
    FTy = VVAR * (VAR(pre_rect_wf_y0) + VAR(pre_rect_wf_dy) * random01());
    return TRUE;
}
