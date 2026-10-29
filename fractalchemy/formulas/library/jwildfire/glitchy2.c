/*
    Fractalchemy formula library — translated from the JWildfire variation
        Glitchy2Func.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    int glitchy2_mode;
    double glitchy2_lr_spin;
    double glitchy2_lr_x;
    double glitchy2_lr_shiftx;
    double glitchy2_lr_y;
    double glitchy2_lr_shifty;
    double glitchy2_lr_re_a;
    double glitchy2_lr_re_b;
    double glitchy2_lr_re_c;
    double glitchy2_lr_re_d;
    double glitchy2_lr_im_a;
    double glitchy2_lr_im_b;
    double glitchy2_lr_im_c;
    double glitchy2_lr_im_d;
    double glitchy2_ur_spin;
    double glitchy2_ur_x;
    double glitchy2_ur_shiftx;
    double glitchy2_ur_y;
    double glitchy2_ur_shifty;
    double glitchy2_ur_re_a;
    double glitchy2_ur_re_b;
    double glitchy2_ur_re_c;
    double glitchy2_ur_re_d;
    double glitchy2_ur_im_a;
    double glitchy2_ur_im_b;
    double glitchy2_ur_im_c;
    double glitchy2_ur_im_d;
    double glitchy2_ll_spin;
    double glitchy2_ll_x;
    double glitchy2_ll_shiftx;
    double glitchy2_ll_y;
    double glitchy2_ll_shifty;
    double glitchy2_ll_re_a;
    double glitchy2_ll_re_b;
    double glitchy2_ll_re_c;
    double glitchy2_ll_re_d;
    double glitchy2_ll_im_a;
    double glitchy2_ll_im_b;
    double glitchy2_ll_im_c;
    double glitchy2_ll_im_d;
    double glitchy2_ul_spin;
    double glitchy2_ul_x;
    double glitchy2_ul_shiftx;
    double glitchy2_ul_y;
    double glitchy2_ul_shifty;
    double glitchy2_ul_re_a;
    double glitchy2_ul_re_b;
    double glitchy2_ul_re_c;
    double glitchy2_ul_re_d;
    double glitchy2_ul_im_a;
    double glitchy2_ul_im_b;
    double glitchy2_ul_im_c;
    double glitchy2_ul_im_d;
    double glitchy2_lr_pz_sin;
    double glitchy2_lr_pz_cos;
    double glitchy2_ur_pz_sin;
    double glitchy2_ur_pz_cos;
    double glitchy2_ll_pz_sin;
    double glitchy2_ll_pz_cos;
    double glitchy2_ul_pz_sin;
    double glitchy2_ul_pz_cos;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("glitchy2");

APO_VARIABLES(
    VAR_INTEGER(glitchy2_mode, 0),
    VAR_REAL(glitchy2_lr_spin, 1),
    VAR_REAL(glitchy2_lr_x, 0),
    VAR_REAL(glitchy2_lr_shiftx, 0),
    VAR_REAL(glitchy2_lr_y, 0),
    VAR_REAL(glitchy2_lr_shifty, 0),
    VAR_REAL(glitchy2_lr_re_a, 0),
    VAR_REAL(glitchy2_lr_re_b, 0),
    VAR_REAL(glitchy2_lr_re_c, 0),
    VAR_REAL(glitchy2_lr_re_d, 1),
    VAR_REAL(glitchy2_lr_im_a, 0),
    VAR_REAL(glitchy2_lr_im_b, 0),
    VAR_REAL(glitchy2_lr_im_c, 0),
    VAR_REAL(glitchy2_lr_im_d, 0),
    VAR_REAL(glitchy2_ur_spin, -1),
    VAR_REAL(glitchy2_ur_x, 0),
    VAR_REAL(glitchy2_ur_shiftx, 0),
    VAR_REAL(glitchy2_ur_y, 0),
    VAR_REAL(glitchy2_ur_shifty, 0),
    VAR_REAL(glitchy2_ur_re_a, 0),
    VAR_REAL(glitchy2_ur_re_b, 0),
    VAR_REAL(glitchy2_ur_re_c, 0),
    VAR_REAL(glitchy2_ur_re_d, 1),
    VAR_REAL(glitchy2_ur_im_a, 0),
    VAR_REAL(glitchy2_ur_im_b, 0),
    VAR_REAL(glitchy2_ur_im_c, 0),
    VAR_REAL(glitchy2_ur_im_d, 0),
    VAR_REAL(glitchy2_ll_spin, -1),
    VAR_REAL(glitchy2_ll_x, 0),
    VAR_REAL(glitchy2_ll_shiftx, 0),
    VAR_REAL(glitchy2_ll_y, 0),
    VAR_REAL(glitchy2_ll_shifty, 0),
    VAR_REAL(glitchy2_ll_re_a, 0),
    VAR_REAL(glitchy2_ll_re_b, 0),
    VAR_REAL(glitchy2_ll_re_c, 0),
    VAR_REAL(glitchy2_ll_re_d, 1),
    VAR_REAL(glitchy2_ll_im_a, 0),
    VAR_REAL(glitchy2_ll_im_b, 0),
    VAR_REAL(glitchy2_ll_im_c, 0),
    VAR_REAL(glitchy2_ll_im_d, 0),
    VAR_REAL(glitchy2_ul_spin, 1),
    VAR_REAL(glitchy2_ul_x, 0),
    VAR_REAL(glitchy2_ul_shiftx, 0),
    VAR_REAL(glitchy2_ul_y, 0),
    VAR_REAL(glitchy2_ul_shifty, 0),
    VAR_REAL(glitchy2_ul_re_a, 0),
    VAR_REAL(glitchy2_ul_re_b, 0),
    VAR_REAL(glitchy2_ul_re_c, 0),
    VAR_REAL(glitchy2_ul_re_d, 1),
    VAR_REAL(glitchy2_ul_im_a, 0),
    VAR_REAL(glitchy2_ul_im_b, 0),
    VAR_REAL(glitchy2_ul_im_c, 0),
    VAR_REAL(glitchy2_ul_im_d, 0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(glitchy2_lr_pz_sin) = sin(VAR(glitchy2_lr_spin) * M_PI_2);
    VAR(glitchy2_lr_pz_cos) = cos(VAR(glitchy2_lr_spin) * M_PI_2);
    VAR(glitchy2_ur_pz_sin) = sin(VAR(glitchy2_ur_spin) * M_PI_2);
    VAR(glitchy2_ur_pz_cos) = cos(VAR(glitchy2_ur_spin) * M_PI_2);
    VAR(glitchy2_ll_pz_sin) = sin(VAR(glitchy2_ll_spin) * M_PI_2);
    VAR(glitchy2_ll_pz_cos) = cos(VAR(glitchy2_ll_spin) * M_PI_2);
    VAR(glitchy2_ul_pz_sin) = sin(VAR(glitchy2_ul_spin) * M_PI_2);
    VAR(glitchy2_ul_pz_cos) = cos(VAR(glitchy2_ul_spin) * M_PI_2);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    int count = 0;
    double x = 0.0;
    double y = 0.0;
    if(FTx > VAR(glitchy2_lr_shiftx) && FTy > VAR(glitchy2_lr_shifty)) {
        double lr_re_u = VAR(glitchy2_lr_re_a) * FTx - VAR(glitchy2_lr_im_a) * FTy + VAR(glitchy2_lr_re_b);
        double lr_im_u = VAR(glitchy2_lr_re_a) * FTy + VAR(glitchy2_lr_im_a) * FTx + VAR(glitchy2_lr_im_b);
        double lr_re_v = VAR(glitchy2_lr_re_c) * FTx - VAR(glitchy2_lr_im_c) * FTy + VAR(glitchy2_lr_re_d);
        double lr_im_v = VAR(glitchy2_lr_re_c) * FTy + VAR(glitchy2_lr_im_c) * FTx + VAR(glitchy2_lr_im_d);
        double d = (lr_re_v * lr_re_v + lr_im_v * lr_im_v);
        if(d == 0) {
            return;
        }
        x += VVAR * (VAR(glitchy2_lr_pz_sin) * FTy + VAR(glitchy2_lr_pz_cos) * FTx) + VAR(glitchy2_lr_x) + (d * (lr_re_u * lr_re_v + lr_im_u * lr_im_v));
        y += VVAR * (VAR(glitchy2_lr_pz_cos) * FTy - VAR(glitchy2_lr_pz_sin) * FTx) + VAR(glitchy2_lr_y) + (d * (lr_im_u * lr_re_v - lr_re_u * lr_im_v));
        count += 1;
    }
    if(FTx > VAR(glitchy2_ur_shiftx) && FTy < VAR(glitchy2_ur_shifty)) {
        double ur_re_u = VAR(glitchy2_ur_re_a) * FTx - VAR(glitchy2_ur_im_a) * FTy + VAR(glitchy2_ur_re_b);
        double ur_im_u = VAR(glitchy2_ur_re_a) * FTy + VAR(glitchy2_ur_im_a) * FTx + VAR(glitchy2_ur_im_b);
        double ur_re_v = VAR(glitchy2_ur_re_c) * FTx - VAR(glitchy2_ur_im_c) * FTy + VAR(glitchy2_ur_re_d);
        double ur_im_v = VAR(glitchy2_ur_re_c) * FTy + VAR(glitchy2_ur_im_c) * FTx + VAR(glitchy2_ur_im_d);
        double d = (ur_re_v * ur_re_v + ur_im_v * ur_im_v);
        if(d == 0) {
            return;
        }
        x += VVAR * (VAR(glitchy2_ur_pz_sin) * FTy + VAR(glitchy2_ur_pz_cos) * FTx) + VAR(glitchy2_ur_x) + (d * (ur_re_u * ur_re_v + ur_im_u * ur_im_v));
        y += VVAR * (VAR(glitchy2_ur_pz_cos) * FTy - VAR(glitchy2_ur_pz_sin) * FTx) + VAR(glitchy2_ur_y) + (d * (ur_im_u * ur_re_v - ur_re_u * ur_im_v));
        count += 1;
    }
    if(FTx < VAR(glitchy2_ll_shiftx) && FTy > VAR(glitchy2_ll_shifty)) {
        double ll_re_u = VAR(glitchy2_ll_re_a) * FTx - VAR(glitchy2_ll_im_a) * FTy + VAR(glitchy2_ll_re_b);
        double ll_im_u = VAR(glitchy2_ll_re_a) * FTy + VAR(glitchy2_ll_im_a) * FTx + VAR(glitchy2_ll_im_b);
        double ll_re_v = VAR(glitchy2_ll_re_c) * FTx - VAR(glitchy2_ll_im_c) * FTy + VAR(glitchy2_ll_re_d);
        double ll_im_v = VAR(glitchy2_ll_re_c) * FTy + VAR(glitchy2_ll_im_c) * FTx + VAR(glitchy2_ll_im_d);
        double d = (ll_re_v * ll_re_v + ll_im_v * ll_im_v);
        if(d == 0) {
            return;
        }
        x += VVAR * (VAR(glitchy2_ll_pz_sin) * FTy + VAR(glitchy2_ll_pz_cos) * FTx) + VAR(glitchy2_ll_x) + (d * (ll_re_u * ll_re_v + ll_im_u * ll_im_v));
        y += VVAR * (VAR(glitchy2_ll_pz_cos) * FTy - VAR(glitchy2_ll_pz_sin) * FTx) + VAR(glitchy2_ll_y) + (d * (ll_im_u * ll_re_v - ll_re_u * ll_im_v));
        count += 1;
    }
    if(FTx < VAR(glitchy2_ul_shiftx) && FTy < VAR(glitchy2_ul_shifty)) {
        double ul_re_u = VAR(glitchy2_ul_re_a) * FTx - VAR(glitchy2_ul_im_a) * FTy + VAR(glitchy2_ul_re_b);
        double ul_im_u = VAR(glitchy2_ul_re_a) * FTy + VAR(glitchy2_ul_im_a) * FTx + VAR(glitchy2_ul_im_b);
        double ul_re_v = VAR(glitchy2_ul_re_c) * FTx - VAR(glitchy2_ul_im_c) * FTy + VAR(glitchy2_ul_re_d);
        double ul_im_v = VAR(glitchy2_ul_re_c) * FTy + VAR(glitchy2_ul_im_c) * FTx + VAR(glitchy2_ul_im_d);
        double d = (ul_re_v * ul_re_v + ul_im_v * ul_im_v);
        if(d == 0) {
            return;
        }
        x += VVAR * (VAR(glitchy2_ul_pz_sin) * FTy + VAR(glitchy2_ul_pz_cos) * FTx) + VAR(glitchy2_ul_x) + (d * (ul_re_u * ul_re_v + ul_im_u * ul_im_v));
        y += VVAR * (VAR(glitchy2_ul_pz_cos) * FTy - VAR(glitchy2_ul_pz_sin) * FTx) + VAR(glitchy2_ul_y) + (d * (ul_im_u * ul_re_v - ul_re_u * ul_im_v));
        count += 1;
    }
    if(VAR(glitchy2_mode) != 0) {
        if(count == 0) {
            FPx += VVAR / FTy;
            FPy += VVAR / FTx;
        } else {
            FPx += VVAR / y / count;
            FPy += VVAR / x / count;
        }
    } else {
        if(count == 0) {
            FPx += VVAR * FTx;
            FPy += VVAR * FTy;
        } else {
            FPx += VVAR * x / count;
            FPy += VVAR * y / count;
        }
    }
    
    return TRUE;
}
