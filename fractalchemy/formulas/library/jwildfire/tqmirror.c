/*
    Fractalchemy formula library — translated from the JWildfire variation
        TQMirrorFunc.java
        by Nic Anderson
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    int tqmirror_preset;
    double tqmirror_a;
    double tqmirror_b;
    double tqmirror_c;
    double tqmirror_d;
    double tqmirror_e;
    double tqmirror_f;
    double tqmirror_g;
    double tqmirror_h;
    double tqmirror_i;
    double tqmirror_j;
    double tqmirror_k;
    double tqmirror_l;
    double tqmirror_m;
    double tqmirror_n;
    double tqmirror_o;
    double tqmirror_p;
    double tqmirror_q;
    double tqmirror_r;
    double tqmirror_s;
    int tqmirror_type;
    int tqmirror_mode;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("tqmirror");

APO_VARIABLES(
    VAR_INTEGER(tqmirror_preset, 0),
    VAR_REAL(tqmirror_a, 1),
    VAR_REAL(tqmirror_b, 1),
    VAR_REAL(tqmirror_c, 1),
    VAR_REAL(tqmirror_d, 1),
    VAR_REAL(tqmirror_e, 1),
    VAR_REAL(tqmirror_f, 1),
    VAR_REAL(tqmirror_g, 1),
    VAR_REAL(tqmirror_h, 1),
    VAR_REAL(tqmirror_i, 1),
    VAR_REAL(tqmirror_j, 1),
    VAR_REAL(tqmirror_k, 1),
    VAR_REAL(tqmirror_l, 0),
    VAR_REAL(tqmirror_m, 0),
    VAR_REAL(tqmirror_n, 0),
    VAR_REAL(tqmirror_o, 0),
    VAR_REAL(tqmirror_p, 0),
    VAR_REAL(tqmirror_q, 0),
    VAR_REAL(tqmirror_r, 1),
    VAR_REAL(tqmirror_s, 1),
    VAR_INTEGER(tqmirror_type, 0),
    VAR_INTEGER(tqmirror_mode, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double x = FTx;
    double y = FTy;
    if(VVAR * VAR(tqmirror_d) + x < VAR(tqmirror_l) || VVAR * VAR(tqmirror_e) + y < VAR(tqmirror_m)) {
        if(VAR(tqmirror_type) != 0) {
            FPx += x * VAR(tqmirror_r);
            FPy += y * VAR(tqmirror_s);
        } else {
            FPx += y * VAR(tqmirror_r);
            FPy += x * VAR(tqmirror_s);
            
        }
        return;
    }
    if(x < VAR(tqmirror_n) && y < VAR(tqmirror_o)) {
        FPx += x + VVAR * VAR(tqmirror_f);
        FPy += y + VVAR * VAR(tqmirror_g);
    } else {
        if(VAR(tqmirror_mode) == 0) {
            if(x + VAR(tqmirror_q) < VVAR && y < VVAR * VAR(tqmirror_a) && x + VVAR * VAR(tqmirror_b) > VAR(tqmirror_l) && y + VVAR * VAR(tqmirror_c) > VAR(tqmirror_p)) {
                FPx -= y * VAR(tqmirror_h);
                FPy -= x * VAR(tqmirror_i);
            } else {
                FPx += x * VAR(tqmirror_j);
                FPy += y * VAR(tqmirror_k);
            }
        } else if(VAR(tqmirror_mode) == 1) {
            if(x + VAR(tqmirror_q) < VVAR && y < VVAR * VAR(tqmirror_a) && x + VVAR * VAR(tqmirror_b) > VAR(tqmirror_l) && y + VVAR * VAR(tqmirror_c) > VAR(tqmirror_p)) {
                FPx -= y * VAR(tqmirror_h);
                FPy -= x * VAR(tqmirror_i);
            } else {
                FPx -= x * VAR(tqmirror_j);
                FPy -= y * VAR(tqmirror_k);
            }
        } else if(VAR(tqmirror_mode) == 2) {
            if(x + VAR(tqmirror_q) < VVAR && y < VVAR * VAR(tqmirror_a) && x + VVAR * VAR(tqmirror_b) > VAR(tqmirror_l) && y + VVAR * VAR(tqmirror_c) > VAR(tqmirror_p)) {
                FPx += y * VAR(tqmirror_h);
                FPy -= x * VAR(tqmirror_i);
            } else {
                FPx += x * VAR(tqmirror_j);
                FPy -= y * VAR(tqmirror_k);
            }
        }
    }
    
    return TRUE;
}
