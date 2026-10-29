/*
    Fractalchemy formula library — translated from the JWildfire variation
        OakLeafFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double oak_leaf_filled;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("oak_leaf");

APO_VARIABLES(
    VAR_REAL(oak_leaf_filled, 0.25)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t = - atan2(FTx, FTy) * 0.5 - M_PI_2;
    double r = (VAR(oak_leaf_filled) > 0 && VAR(oak_leaf_filled) > random01()) ? VVAR * random01() * 2.0 : VVAR * 2.0;
    double lx = (pow(cos(t), 9.0)) / 100.0 * pow(cos(5.0 * t), 10.0) + sin(2.0 * t) / 4.0 * (1.0 - pow(sin(10.0 * t), 2.0) / 2.0) * (1.0 - (pow(cos(t) * cos(3.0 * t), 8.0)));
    double ly = sin(t) * (1.0 - pow(sin(10.0 * t), 2.0) / 5.0 * (0.5 + pow(sin(2.0 * t), 2.0)));
    FPx += r * lx;
    FPy += r * ly;
    
    return TRUE;
}
