/*
    Fractalchemy formula library — translated from the JWildfire variation
        HeartWFFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double heart_wf_scale_x;
    double heart_wf_shift_t;
    double heart_wf_scale_r_left;
    double heart_wf_scale_r_right;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("heart_wf");

APO_VARIABLES(
    VAR_REAL(heart_wf_scale_x, 1),
    VAR_REAL(heart_wf_shift_t, 0),
    VAR_REAL(heart_wf_scale_r_left, 1),
    VAR_REAL(heart_wf_scale_r_right, 1)
);

#define T_MAX (60.0)

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double a = atan2(FTx, FTy);
    double r = sqrt(FTx * FTx + FTy * FTy);
    double nx, t;
    if(a < 0) {
        t = - a / M_PI * T_MAX * VAR(heart_wf_scale_r_left) - VAR(heart_wf_shift_t);
        if(t > T_MAX) {
            t = T_MAX;
        }
        nx = - 0.001 * (- t * t + 40 * t + 1200) * sin(M_PI * t / 180.0) * r;
    } else {
        t = a / M_PI * T_MAX * VAR(heart_wf_scale_r_right) - VAR(heart_wf_shift_t);
        if(t > T_MAX) {
            t = T_MAX;
        }
        nx = 0.001 * (- t * t + 40 * t + 1200) * sin(M_PI * t / 180.0) * r;
    }
    double ny = - 0.001 * (- t * t + 40 * t + 400) * cos(M_PI * t / 180.0) * r;
    nx *= VAR(heart_wf_scale_x);
    FPx += VVAR * nx;
    FPy += VVAR * ny;
    
    return TRUE;
}
