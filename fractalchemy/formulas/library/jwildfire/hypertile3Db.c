/*
    Fractalchemy formula library — translated from the JWildfire variation
        Hypertile3DbFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    int hypertile3Db_p;
    int hypertile3Db_q;
    int hypertile3Db_n;
    double hypertile3Db_b;
    double hypertile3Db_c;
    double hypertile3Db_d;
    double hypertile3Db_e;
    double hypertile3Db_f;
    double hypertile3Db_g;
    double hypertile3Db_h;
    double hypertile3Db_i;
    double hypertile3Db_j;
    double hypertile3Db_k;
    double hypertile3Db_c2x;
    double hypertile3Db_c2y;
    double hypertile3Db_c2;
    double hypertile3Db_s2x;
    double hypertile3Db_s2y;
    double hypertile3Db_s2z;
    double hypertile3Db_cx;
    double hypertile3Db_cy;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("hypertile3Db");

APO_VARIABLES(
    VAR_INTEGER(hypertile3Db_p, 3),
    VAR_INTEGER(hypertile3Db_q, 7),
    VAR_INTEGER(hypertile3Db_n, 0),
    VAR_REAL(hypertile3Db_b, 2),
    VAR_REAL(hypertile3Db_c, 2),
    VAR_REAL(hypertile3Db_d, 1),
    VAR_REAL(hypertile3Db_e, 1),
    VAR_REAL(hypertile3Db_f, 1),
    VAR_REAL(hypertile3Db_g, 2),
    VAR_REAL(hypertile3Db_h, 2),
    VAR_REAL(hypertile3Db_i, 1),
    VAR_REAL(hypertile3Db_j, 1),
    VAR_REAL(hypertile3Db_k, 1)
);

int PluginVarPrepare(Variation* vp)
{
    double pa = VAR(hypertile3Db_b) * M_PI / VAR(hypertile3Db_p), qa = VAR(hypertile3Db_c) * M_PI / VAR(hypertile3Db_q);
    double r = - (cos(pa) - VAR(hypertile3Db_d)) / (cos(pa) + cos(qa));
    if(r > 0) r = VAR(hypertile3Db_e) / sqrt(VAR(hypertile3Db_f) + r);
    else r = 1;
    double na = VAR(hypertile3Db_n) * pa;
    VAR(hypertile3Db_cx) = r * cos(na);
    VAR(hypertile3Db_cy) = r * sin(na);
    VAR(hypertile3Db_c2) = sqr(VAR(hypertile3Db_cx)) + sqr(VAR(hypertile3Db_cy));
    VAR(hypertile3Db_c2x) = VAR(hypertile3Db_g) * VAR(hypertile3Db_cx);
    VAR(hypertile3Db_c2y) = VAR(hypertile3Db_h) * VAR(hypertile3Db_cy);
    VAR(hypertile3Db_s2x) = VAR(hypertile3Db_i) + sqr(VAR(hypertile3Db_cx)) - sqr(VAR(hypertile3Db_cy));
    VAR(hypertile3Db_s2y) = VAR(hypertile3Db_j) + sqr(VAR(hypertile3Db_cy)) - sqr(VAR(hypertile3Db_cx));
    VAR(hypertile3Db_s2z) = VAR(hypertile3Db_k) - sqr(VAR(hypertile3Db_cy)) - sqr(VAR(hypertile3Db_cx));
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double r2 = sqr(FTx) + sqr(FTy) + sqr(FTz);
    double x2cx = VAR(hypertile3Db_c2x) * FTx, y2cy = VAR(hypertile3Db_c2y) * FTy;
    double d = VVAR / (VAR(hypertile3Db_c2) * r2 + x2cx - y2cy + 1);
    FPx += d * (FTx * VAR(hypertile3Db_s2x) - VAR(hypertile3Db_cx) * (y2cy - r2 - 1));
    FPy += d * (FTy * VAR(hypertile3Db_s2y) + VAR(hypertile3Db_cy) * (- x2cx - r2 - 1));
    FPz += d * (FTz * VAR(hypertile3Db_s2z));
    return TRUE;
}
