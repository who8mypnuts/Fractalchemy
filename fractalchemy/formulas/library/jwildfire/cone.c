/*
    Fractalchemy formula library — translated from the JWildfire variation
        ConeFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double cone_radius1;
    double cone_radius2;
    double cone_size1;
    double cone_size2;
    double cone_ywave;
    double cone_xwave;
    double cone_height;
    double cone_warp;
    double cone_weight;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("cone");

APO_VARIABLES(
    VAR_REAL(cone_radius1, 0.5),
    VAR_REAL(cone_radius2, 1),
    VAR_REAL(cone_size1, 0.5),
    VAR_REAL(cone_size2, 2),
    VAR_REAL(cone_ywave, 1),
    VAR_REAL(cone_xwave, 1),
    VAR_REAL(cone_height, 1),
    VAR_REAL(cone_warp, 1),
    VAR_REAL(cone_weight, 2)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double r = VVAR / sqrt(FTx * FTx * VAR(cone_warp) + FTy * FTy + VAR(cone_size1)) * VAR(cone_size2);
    double xx = atan2(FTx, FTy) * VAR(cone_radius1) + M_PI * (int)(VAR(cone_weight) * random01()) * VAR(cone_radius2);
    double sina = sin(xx * VAR(cone_ywave));
    double cosa = cos(xx * VAR(cone_xwave));
    FPx += r * cosa;
    FPy += r * sina;
    FPz += r * VAR(cone_height);
    return TRUE;
}
