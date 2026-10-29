/*
    Fractalchemy formula library — translated from the JWildfire variation
        Hypertile3D2bFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    int hypertile3D2b_p;
    int hypertile3D2b_q;
    double hypertile3D2b_b;
    double hypertile3D2b_c;
    double hypertile3D2b_d;
    double hypertile3D2b_e;
    double hypertile3D2b_f;
    double hypertile3D2b_g;
    double hypertile3D2b_h;
    double hypertile3D2b_i;
    double hypertile3D2b_j;
    double hypertile3D2b_k;
    double hypertile3D2b_pa;
    double hypertile3D2b_qa;
    double hypertile3D2b_cx;
    double hypertile3D2b_c2;
    double hypertile3D2b_c2x;
    double hypertile3D2b_s2x;
    double hypertile3D2b_s2y;
    double hypertile3D2b_s2z;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("hypertile3D2b");

APO_VARIABLES(
    VAR_INTEGER(hypertile3D2b_p, 3),
    VAR_INTEGER(hypertile3D2b_q, 7),
    VAR_REAL(hypertile3D2b_b, 2),
    VAR_REAL(hypertile3D2b_c, 2),
    VAR_REAL(hypertile3D2b_d, 1),
    VAR_REAL(hypertile3D2b_e, 1),
    VAR_REAL(hypertile3D2b_f, 1),
    VAR_REAL(hypertile3D2b_g, 2),
    VAR_REAL(hypertile3D2b_h, 1),
    VAR_REAL(hypertile3D2b_i, 1),
    VAR_REAL(hypertile3D2b_j, 1),
    VAR_REAL(hypertile3D2b_k, 1)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(hypertile3D2b_pa) = VAR(hypertile3D2b_b) * M_PI / VAR(hypertile3D2b_p);
    VAR(hypertile3D2b_qa) = VAR(hypertile3D2b_c) * M_PI / VAR(hypertile3D2b_q);
    double r = - (cos(VAR(hypertile3D2b_pa)) - VAR(hypertile3D2b_d)) / (cos(VAR(hypertile3D2b_pa)) + cos(VAR(hypertile3D2b_qa)));
    if(r > 0) r = VAR(hypertile3D2b_e) / sqrt(VAR(hypertile3D2b_f) + r);
    else r = 1;
    VAR(hypertile3D2b_cx) = r;
    VAR(hypertile3D2b_c2) = sqr(VAR(hypertile3D2b_cx));
    VAR(hypertile3D2b_c2x) = VAR(hypertile3D2b_g) * VAR(hypertile3D2b_cx);
    VAR(hypertile3D2b_s2x) = VAR(hypertile3D2b_i) + sqr(VAR(hypertile3D2b_cx));
    VAR(hypertile3D2b_s2y) = VAR(hypertile3D2b_j) - sqr(VAR(hypertile3D2b_cx));
    VAR(hypertile3D2b_s2z) = VAR(hypertile3D2b_k) - sqr(VAR(hypertile3D2b_cx));
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double r2 = sqr(FTx) + sqr(FTy) + sqr(FTz);
    double x2cx = VAR(hypertile3D2b_c2x) * FTx;
    double x = FTx * VAR(hypertile3D2b_s2x) - VAR(hypertile3D2b_cx) * (- r2 - 1);
    double y = FTy * VAR(hypertile3D2b_s2y);
    double vr = VVAR / (VAR(hypertile3D2b_c2) * r2 + x2cx + VAR(hypertile3D2b_h));
    double a = (int)(random01() *  INT_MAX) * VAR(hypertile3D2b_pa);
    double sina = sin(a);
    double cosa = cos(a);
    FPx += vr * (x * cosa + y * sina);
    FPy += vr * (y * cosa - x * sina);
    FPz += vr * (FTz * VAR(hypertile3D2b_s2z));
    return TRUE;
}
