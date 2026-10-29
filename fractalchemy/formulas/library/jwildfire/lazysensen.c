/*
    Fractalchemy formula library — translated from the JWildfire variation
        LazySensenFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double lazysensen_scale_x;
    double lazysensen_scale_y;
    double lazysensen_scale_z;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("lazysensen");

APO_VARIABLES(
    VAR_REAL(lazysensen_scale_x, 1),
    VAR_REAL(lazysensen_scale_y, 1),
    VAR_REAL(lazysensen_scale_z, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    if(VAR(lazysensen_scale_x) != 0.0) {
        double nr = (int) floor(FTx * VAR(lazysensen_scale_x));
        if(nr >= 0) {
            if(nr % 2 == 1) FTx = - FTx;
        } else {
            if(nr % 2 == 0) FTx = - FTx;
        }
    }
    if(VAR(lazysensen_scale_y) != 0.0) {
        double nr = (int) floor(FTy * VAR(lazysensen_scale_y));
        if(nr >= 0) {
            if(nr % 2 == 1) FTy = - FTy;
        } else {
            if(nr % 2 == 0) FTy = - FTy;
        }
    }
    if(VAR(lazysensen_scale_z) != 0.0) {
        double nr = (int) floor(FTz * VAR(lazysensen_scale_z));
        if(nr >= 0) {
            if(nr % 2 == 1) FTz = - FTz;
        } else {
            if(nr % 2 == 0) FTz = - FTz;
        }
    }
    FPx += VVAR * FTx;
    FPy += VVAR * FTy;
    FPz += VVAR * FTz;
    return TRUE;
}
