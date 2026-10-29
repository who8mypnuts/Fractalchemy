/*
    Fractalchemy formula library — translated from the JWildfire variation
        YinYangFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double yin_yang_radius;
    double yin_yang_ang1;
    double yin_yang_ang2;
    int yin_yang_dual_t;
    int yin_yang_outside;
    double yin_yang_sina;
    double yin_yang_cosa;
    double yin_yang_sinb;
    double yin_yang_cosb;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("yin_yang");

APO_VARIABLES(
    VAR_REAL(yin_yang_radius, 0.5),
    VAR_REAL(yin_yang_ang1, 0),
    VAR_REAL(yin_yang_ang2, 0),
    VAR_INTEGER(yin_yang_dual_t, 1),
    VAR_INTEGER(yin_yang_outside, 0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(yin_yang_sina) = sin(M_PI * VAR(yin_yang_ang1));
    VAR(yin_yang_cosa) = cos(M_PI * VAR(yin_yang_ang1));
    VAR(yin_yang_sinb) = sin(M_PI * VAR(yin_yang_ang2));
    VAR(yin_yang_cosb) = cos(M_PI * VAR(yin_yang_ang2));
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double xx = FTx;
    double yy = FTy;
    double inv = 1;
    double RR = VAR(yin_yang_radius);
    double R2 = (xx * xx + yy * yy);
    if(R2 < 1.0) {
        double nx = xx * VAR(yin_yang_cosa) - yy * VAR(yin_yang_sina);
        double ny = xx * VAR(yin_yang_sina) + yy * VAR(yin_yang_cosa);
        if(VAR(yin_yang_dual_t) == 1 && random01() > 0.5) {
            inv = - 1;
            RR = 1 - VAR(yin_yang_radius);
            nx = xx * VAR(yin_yang_cosb) - yy * VAR(yin_yang_sinb);
            ny = xx * VAR(yin_yang_sinb) + yy * VAR(yin_yang_cosb);
        }
        xx = nx;
        yy = ny;
        if(yy > 0) {
            double t = sqrt(1 - yy * yy);
            double k = xx / t;
            double t1 = (t - 0.5) * 2;
            double alfa = (1. - k) * 0.5;
            double beta = (1. - alfa);
            double dx = alfa * (RR - 1);
            double k1 = alfa * (RR) + beta * 1;
            FPx += VVAR * (t1 * k1 + dx) * inv;
            FPy += VVAR * sqrt(1 - t1 * t1) * k1 * inv;
        } else {
            FPx += VVAR * (xx * (1 - RR) + RR) * inv;
            FPy += VVAR * (yy * (1 - RR)) * inv;
        }
    } else if(VAR(yin_yang_outside) == 1) {
        FPx += VVAR * FTx;
        FPy += VVAR * FTy;
    } else {
        FPx += 0.0;
        FPy += 0.0;
    }
    
    return TRUE;
}
