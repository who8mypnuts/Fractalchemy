/*
    Fractalchemy formula library — translated from the JWildfire variation
        ParallelFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double parallel_x1width;
    double parallel_x1tilesize;
    double parallel_x1mod1;
    double parallel_x1mod2;
    double parallel_x1height;
    double parallel_x1move;
    double parallel_x2width;
    double parallel_x2tilesize;
    double parallel_x2mod1;
    double parallel_x2mod2;
    double parallel_x2height;
    double parallel_x2move;
    double parallel__xr1;
    double parallel__xr2;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("parallel");

APO_VARIABLES(
    VAR_REAL(parallel_x1width, 5),
    VAR_REAL(parallel_x1tilesize, 0.5),
    VAR_REAL(parallel_x1mod1, 0.3),
    VAR_REAL(parallel_x1mod2, 1),
    VAR_REAL(parallel_x1height, 0.5),
    VAR_REAL(parallel_x1move, 1),
    VAR_REAL(parallel_x2width, 5),
    VAR_REAL(parallel_x2tilesize, 0.5),
    VAR_REAL(parallel_x2mod1, 0.3),
    VAR_REAL(parallel_x2mod2, 1),
    VAR_REAL(parallel_x2height, 0.5),
    VAR_REAL(parallel_x2move, 1)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(parallel__xr1) = VAR(parallel_x1mod2) * VAR(parallel_x1mod1);
    VAR(parallel__xr2) = VAR(parallel_x2mod2) * VAR(parallel_x2mod1);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    if(random01() < 0.5) {
        double x1 = - VAR(parallel_x1width);
        if(random01() < 0.5) x1 = VAR(parallel_x1width);
        FPx += VAR(parallel_x1tilesize) * (FTx + round(x1 * log(random01())));
        if(FTy > VAR(parallel_x1mod1)) {
            FPy += VAR(parallel_x1height) * (- VAR(parallel_x1mod1) + fmod(FTy + VAR(parallel_x1mod1), VAR(parallel__xr1))) + VVAR * VAR(parallel_x1move);
        } else if(FTy < - VAR(parallel_x1mod1)) {
            FPy += VAR(parallel_x1height) * (VAR(parallel_x1mod1) - fmod(VAR(parallel_x1mod1) - FTy, VAR(parallel__xr1))) + VVAR * VAR(parallel_x1move);
        } else {
            FPy += VAR(parallel_x1height) * FTy + VVAR * VAR(parallel_x1move);
        }
    } else {
        double x2 = - VAR(parallel_x2width);
        if(random01() < 0.5) x2 = VAR(parallel_x2width);
        FPx += VAR(parallel_x2tilesize) * (FTx + round(x2 * log(random01())));
        if(FTy > VAR(parallel_x2mod1)) {
            FPy += VAR(parallel_x2height) * (- VAR(parallel_x2mod1) + fmod(FTy + VAR(parallel_x2mod1), VAR(parallel__xr2))) - VVAR * VAR(parallel_x2move);
        } else if(FTy < - VAR(parallel_x2mod1)) {
            FPy += VAR(parallel_x2height) * (VAR(parallel_x2mod1) - fmod(VAR(parallel_x2mod1) - FTy, VAR(parallel__xr2))) - VVAR * VAR(parallel_x2move);
        } else {
            FPy += VAR(parallel_x2height) * FTy - VVAR * VAR(parallel_x2move);
        }
    }
    
    return TRUE;
}
