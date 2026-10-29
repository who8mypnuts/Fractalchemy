/*
    Fractalchemy formula library — translated from the JWildfire variation
        XHeartBlurWFFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double xheart_blur_wf_angle;
    double xheart_blur_wf_ratio;
    double xheart_blur_wf_rat;
    double xheart_blur_wf_cosa;
    double xheart_blur_wf_sina;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("xheart_blur_wf");

APO_VARIABLES(
    VAR_REAL(xheart_blur_wf_angle, 0),
    VAR_REAL(xheart_blur_wf_ratio, 0)
);

int PluginVarPrepare(Variation* vp)
{
    double ang = M_PI_4 + (0.5 * M_PI_4 * VAR(xheart_blur_wf_angle));
    VAR(xheart_blur_wf_sina) = sin(ang);
    VAR(xheart_blur_wf_cosa) = cos(ang);
    VAR(xheart_blur_wf_rat) = 6 + 2 * VAR(xheart_blur_wf_ratio);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double dx = 2.0 - random01() * 4.0;
    double dy = 2.0 - random01() * 4.0;
    double r2_4 = dx * dx + dy * dy + 4;
    if(r2_4 == 0) r2_4 = 1;
    double bx = 4 / r2_4, by = VAR(xheart_blur_wf_rat) / r2_4;
    double x = VAR(xheart_blur_wf_cosa) * (bx * dx) - VAR(xheart_blur_wf_sina) * (by * dy);
    double y = VAR(xheart_blur_wf_sina) * (bx * dx) + VAR(xheart_blur_wf_cosa) * (by * dy);
    if(x > 0) {
        FPx += VVAR * x;
        FPy += VVAR * y;
    } else {
        FPx += VVAR * x;
        FPy += - VVAR * y;
    }
    
    return TRUE;
}
