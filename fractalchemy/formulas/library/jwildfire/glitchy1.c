/*
    Fractalchemy formula library — translated from the JWildfire variation
        Glitchy1Func.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double glitchy1_scale_x;
    double glitchy1_scale_y;
    double glitchy1_scale_z;
    double glitchy1_shift_x;
    double glitchy1_shift_y;
    double glitchy1_shift_z;
    int glitchy1_n_x;
    int glitchy1_n_y;
    int glitchy1_n_z;
    double glitchy1_width;
    int glitchy1_seed;
    double glitchy1_angle;
    double glitchy1_u;
    double glitchy1_v;
    double glitchy1_w;
    double glitchy1_h;
    double glitchy1_k;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("glitchy1");

APO_VARIABLES(
    VAR_REAL(glitchy1_scale_x, 1),
    VAR_REAL(glitchy1_shift_x, 0),
    VAR_INTEGER(glitchy1_n_x, 2),
    VAR_REAL(glitchy1_scale_y, 1),
    VAR_REAL(glitchy1_shift_y, 0),
    VAR_INTEGER(glitchy1_n_y, 2),
    VAR_REAL(glitchy1_scale_z, 0),
    VAR_REAL(glitchy1_shift_z, 0),
    VAR_INTEGER(glitchy1_n_z, 2),
    VAR_REAL(glitchy1_width, 1),
    VAR_INTEGER(glitchy1_seed, 42),
    VAR_REAL(glitchy1_angle, 30),
    VAR_REAL(glitchy1_u, 1),
    VAR_REAL(glitchy1_v, 1),
    VAR_REAL(glitchy1_w, 1)
);

double radians(double d) { return d * M_PI / 180.0; }
double hash(int a)
{
    a = (a ^ 61) ^ (a >> 16);
    a = a + (a << 3);
    a = a ^ (a >> 4);
    a = a * 0x27d4eb2d;
    a = a ^ (a >> 15);
    return(double) a / (double) INT_MAX;
}

int PluginVarPrepare(Variation* vp)
{
    VAR(glitchy1_h) = sin(radians(VAR(glitchy1_angle)));
    VAR(glitchy1_k) = cos(radians(VAR(glitchy1_angle)));
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double x = FTx;
    double y = FTy;
    double z = FTz;
    if(VAR(glitchy1_scale_x) != 0.0) {
        double nr = (int) floor((x - VAR(glitchy1_shift_x)) * VAR(glitchy1_scale_x));
        if(nr >= 0) {
            if(nr % VAR(glitchy1_n_x) == (VAR(glitchy1_n_x) - 1)) x = 2 * VAR(glitchy1_shift_x) - x;
        } else {
            if(nr % VAR(glitchy1_n_x) == 0) x = 2 * VAR(glitchy1_shift_x) - x;
        }
    }
    if(VAR(glitchy1_scale_y) != 0.0) {
        double nr = (int) floor((y - VAR(glitchy1_shift_y)) * VAR(glitchy1_scale_y));
        if(nr >= 0) {
            if(nr % VAR(glitchy1_n_y) == (VAR(glitchy1_n_y) - 1)) y = 2 * VAR(glitchy1_shift_y) - y;
        } else {
            if(nr % VAR(glitchy1_n_y) == 0) y = 2 * VAR(glitchy1_shift_y) - y;
        }
    }
    if(VAR(glitchy1_scale_z) != 0.0) {
        double nr = (int) floor((z - VAR(glitchy1_shift_z)) * VAR(glitchy1_scale_z));
        if(nr >= 0) {
            if(nr % VAR(glitchy1_n_z) == (VAR(glitchy1_n_z) - 1)) z = 2 * VAR(glitchy1_shift_z) - z;
        } else {
            if(nr % VAR(glitchy1_n_z) == 0) z = 2 * VAR(glitchy1_shift_z) - z;
        }
    }
    double uu = VAR(glitchy1_u) * FTx;
    double vv = VAR(glitchy1_v) * (VAR(glitchy1_k) * uu + VAR(glitchy1_h) * FTy);
    double ww = VAR(glitchy1_w) * (VAR(glitchy1_k) * uu - VAR(glitchy1_h) * FTy);
    int blocku = (int) floor(uu * VAR(glitchy1_width));
    blocku += (2.0 - 4.0 * hash(blocku * VAR(glitchy1_seed) + 1));
    int blockv = (int) floor(vv * VAR(glitchy1_width));
    blockv += (2.0 - 4.0 * hash(blockv * VAR(glitchy1_seed) + 1));
    int blockw = (int) floor(ww * VAR(glitchy1_width));
    blockw += (2.0 - 4.0 * hash(blockw * VAR(glitchy1_seed) + 1));
    double fLen = (hash(blocku + blockv + blockw * - VAR(glitchy1_seed)) + hash(blocku + blockv + blockw * VAR(glitchy1_seed) / 2));
    FPx += VVAR * x * fLen;
    FPy += VVAR * y * fLen;
    FPz += VVAR * z * fLen;
    return TRUE;
}
