/*
    Fractalchemy formula library — translated from the JWildfire variation
        Cell2Func.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double cell2_size;
    int cell2_mirror_x;
    int cell2_mirror_y;
    double cell2_a;
    double cell2_space_ya;
    double cell2_space_xa;
    double cell2_space_yb;
    double cell2_space_xb;
    double cell2_move_xa;
    double cell2_space_yc;
    double cell2_move_ya;
    double cell2_space_xc;
    double cell2_space_yd;
    double cell2_move_yb;
    double cell2_space_xd;
    double cell2_move_xb;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("cell2");

APO_VARIABLES(
    VAR_REAL(cell2_size, 0.6),
    VAR_INTEGER(cell2_mirror_x, 0),
    VAR_INTEGER(cell2_mirror_y, 0),
    VAR_REAL(cell2_a, 1),
    VAR_REAL(cell2_space_ya, 2),
    VAR_REAL(cell2_space_xa, 2),
    VAR_REAL(cell2_space_yb, 2),
    VAR_REAL(cell2_space_xb, 2),
    VAR_REAL(cell2_move_xa, 1),
    VAR_REAL(cell2_space_yc, 2),
    VAR_REAL(cell2_move_ya, 1),
    VAR_REAL(cell2_space_xc, 2),
    VAR_REAL(cell2_space_yd, 2),
    VAR_REAL(cell2_move_yb, 1),
    VAR_REAL(cell2_space_xd, 2),
    VAR_REAL(cell2_move_xb, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double inv_cell_size = VAR(cell2_a) / VAR(cell2_size);
    double x = (int) floor(FTx * inv_cell_size);
    double y = (int) floor(FTy * inv_cell_size);
    double dx = FTx - x * VAR(cell2_size);
    double dy = FTy - y * VAR(cell2_size);
    if(y >= 0) {
        if(x >= 0) {
            y *= VAR(cell2_space_ya);
            x *= VAR(cell2_space_xa);
        } else {
            y *= VAR(cell2_space_yb);
            x = - (VAR(cell2_space_xb) * x + VAR(cell2_move_xa));
        }
    } else {
        if(x >= 0) {
            y = - (VAR(cell2_space_yc) * y + VAR(cell2_move_ya));
            x *= VAR(cell2_space_xc);
        } else {
            y = - (VAR(cell2_space_yd) * y + VAR(cell2_move_yb));
            x = - (VAR(cell2_space_xd) * x + VAR(cell2_move_xb));
        }
    }
    FPx += VVAR * (dx + x * VAR(cell2_size));
    FPy -= VVAR * (dy + y * VAR(cell2_size));
    if(VAR(cell2_mirror_x) > 0 && random01() < 0.5) {
        FPx = - FPx;
    }
    if(VAR(cell2_mirror_y) > 0 && random01() < 0.5) {
        FPy = - FPy;
    }
    
    return TRUE;
}
