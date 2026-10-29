/*
    Fractalchemy formula library — translated from the JWildfire variation
        IntersectionFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double intersection_xwidth;
    double intersection_xtilesize;
    double intersection_xmod1;
    double intersection_xmod2;
    double intersection_xheight;
    double intersection_yheight;
    double intersection_ytilesize;
    double intersection_ymod1;
    double intersection_ymod2;
    double intersection_ywidth;
    double intersection__xr1;
    double intersection__yr1;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("intersection");

APO_VARIABLES(
    VAR_REAL(intersection_xwidth, 5),
    VAR_REAL(intersection_xtilesize, 0.5),
    VAR_REAL(intersection_xmod1, 0.3),
    VAR_REAL(intersection_xmod2, 1),
    VAR_REAL(intersection_xheight, 0.5),
    VAR_REAL(intersection_yheight, 5),
    VAR_REAL(intersection_ytilesize, 0.5),
    VAR_REAL(intersection_ymod1, 0.3),
    VAR_REAL(intersection_ymod2, 1),
    VAR_REAL(intersection_ywidth, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(intersection__xr1) = VAR(intersection_xmod2) * VAR(intersection_xmod1);
    VAR(intersection__yr1) = VAR(intersection_ymod2) * VAR(intersection_ymod1);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    if(random01() < 0.5) {
        double x = - VAR(intersection_xwidth);
        if(random01() < 0.5) x = VAR(intersection_xwidth);
        FPx += VAR(intersection_xtilesize) * (FTx + round(x * log(random01())));
        if(FTy > VAR(intersection_xmod1)) {
            FPy += VAR(intersection_xheight) * (- VAR(intersection_xmod1) + fmod(FTy + VAR(intersection_xmod1), VAR(intersection__xr1)));
        } else if(FTy < - VAR(intersection_xmod1)) {
            FPy += VAR(intersection_xheight) * (VAR(intersection_xmod1) - fmod(VAR(intersection_xmod1) - FTy, VAR(intersection__xr1)));
        } else {
            FPy += VAR(intersection_xheight) * FTy;
        }
    } else {
        double y = - VAR(intersection_yheight);
        if(random01() < 0.5) y = VAR(intersection_yheight);
        FPy += VAR(intersection_ytilesize) * (FTy + round(y * log(random01())));
        if(FTx > VAR(intersection_ymod1)) {
            FPx += VAR(intersection_ywidth) * (- VAR(intersection_ymod1) + fmod(FTx + VAR(intersection_ymod1), VAR(intersection__yr1)));
        } else if(FTx < - VAR(intersection_ymod1)) {
            FPx += VAR(intersection_ywidth) * (VAR(intersection_ymod1) - fmod(VAR(intersection_ymod1) - FTx, VAR(intersection__yr1)));
        } else {
            FPx += VAR(intersection_ywidth) * FTx;
        }
    }
    
    return TRUE;
}
