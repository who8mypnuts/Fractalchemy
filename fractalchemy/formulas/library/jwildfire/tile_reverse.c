/*
    Fractalchemy formula library — translated from the JWildfire variation
        Tile_Reverse_Func.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

// keeps a private orbit between points (JWildfire fields updated per point): the statics below
typedef struct {
    double tile_reverse_space;
    double tile_reverse_reversal;
    int tile_reverse_vertical;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("tile_reverse");

APO_VARIABLES(
    VAR_REAL(tile_reverse_space, 1),
    VAR_REAL(tile_reverse_reversal, 1),
    VAR_INTEGER(tile_reverse_vertical, 0)
);

static double rev = -1;

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double n = random01();
    if(VAR(tile_reverse_reversal) == 1) {
        rev = - 1;
    } else {
        rev = 1;
    }
    if(n < 0.5 && VAR(tile_reverse_vertical) != 1) {
        FPx = VVAR * (rev * FTx) + (VAR(tile_reverse_space));
        FPy = VVAR * FTy;
    } else if(n > 0.5 && VAR(tile_reverse_vertical) != 1) {
        FPx = VVAR * (rev * FTx) - (VAR(tile_reverse_space));
        FPy = VVAR * FTy;
    } else if(n < 0.5 && VAR(tile_reverse_vertical) == 1) {
        FPy = VVAR * (rev * FTy) + (VAR(tile_reverse_space));
        FPx = VVAR * FTx;
    } else if(n > 0.5 && VAR(tile_reverse_vertical) == 1) {
        FPy = VVAR * (rev * FTy) - (VAR(tile_reverse_space));
        FPx = VVAR * FTx;
    }
    
    return TRUE;
}
