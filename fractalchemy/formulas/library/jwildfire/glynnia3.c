/*
    Fractalchemy formula library — translated from the JWildfire variation
        Glynnia3Func.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double glynnia3_rscale;
    double glynnia3_dscale;
    double glynnia3_rthresh;
    double glynnia3_ythresh;
    double glynnia3__vvar2;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("glynnia3");

APO_VARIABLES(
    VAR_REAL(glynnia3_rscale, 1),
    VAR_REAL(glynnia3_dscale, 1),
    VAR_REAL(glynnia3_rthresh, 0),
    VAR_REAL(glynnia3_ythresh, 0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(glynnia3__vvar2) = VVAR * sqrt(2.0) / 2.0;
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double r = VAR(glynnia3_rscale) * (sqrt(sqr(FTx) + sqr(FTy)));
    double d;
    if(r > VAR(glynnia3_rthresh) && FTy > VAR(glynnia3_ythresh)) {
        if(random01() > 0.5) {
            d = VAR(glynnia3_dscale) * sqrt(r + FTx);
            if(d == 0) {
                return;
            }
            FPx += VAR(glynnia3__vvar2) * d;
            FPy -= VAR(glynnia3__vvar2) / d * FTy;
        } else {
            d = VAR(glynnia3_dscale) * (r + FTx);
            double dx = sqrt(r * (sqr(FTy) + sqr(d)));
            if(dx == 0) {
                return;
            }
            r = VVAR / dx;
            FPx += r * d;
            FPy += r * FTy;
        }
    } else {
        if(random01() > 0.5) {
            d = VAR(glynnia3_dscale) * sqrt(r + FTx);
            if(d == 0) {
                return;
            }
            FPx -= VAR(glynnia3__vvar2) * d;
            FPy -= VAR(glynnia3__vvar2) / d * FTy;
        } else {
            d = VAR(glynnia3_dscale) * (r + FTx);
            double dx = sqrt(r * (sqr(FTy) + sqr(d)));
            if(dx == 0) {
                return;
            }
            r = VVAR / dx;
            FPx -= r * d;
            FPy += r * FTy;
        }
    }
    
    return TRUE;
}
