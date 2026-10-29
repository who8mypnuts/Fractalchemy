/*
    Fractalchemy formula library — translated from the JWildfire variation
        JapaneseMapleLeafFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double japanese_maple_leaf_filled;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("japanese_maple_leaf");

APO_VARIABLES(
    VAR_REAL(japanese_maple_leaf_filled, 0.15)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t = atan2(FTx, FTy) * 0.5 + M_PI_2;
    double scale = 0.667;
    double r = (VAR(japanese_maple_leaf_filled) > 0 && VAR(japanese_maple_leaf_filled) > random01()) ? VVAR * random01() * scale : VVAR * scale;
    double lx = (4.0 / 15.0 + pow(cos(8.0 * t), 2.0) + 1.0 / 5.0 * pow(cos(8.0 * t) * cos(24.0 * t), 10.0) + (1.0 / 6.0 * pow(cos(80.0 * t), 2.0) + 1.0 / 15.0 * pow(cos(80.0 * t), 10.0))) * (1.0 - pow(sin(8.0 * t), 10.0)) * sin(2.0 * t) * (1.0 + sin(t)) * (1 - pow(cos(t), 10.0) * pow(cos(3.0 * t), 2.0) + 1.0 / 30.0 * pow(cos(t), 9.0) * pow(cos(5.0 * t), 10.0));
    double ly = (8.0 / 30.0 + pow(cos(8.0 * t), 2.0) + 1.0 / 5.0 * pow(cos(8.0 * t) * cos(24.0 * t), 10.0) + (1.0 / 6.0 * pow(cos(80.0 * t), 2.0) + 1.0 / 15.0 * pow(cos(80.0 * t), 10.0)) * (1.0 - pow(cos(t), 10.0) * pow(cos(3.0 * t), 2.0)) * (1.0 - pow(sin(8.0 * t), 10.0))) * cos(2.0 * t) * (1.0 + sin(t) + pow(cos(t) * cos(3.0 * t), 10.0));
    FPx += r * lx;
    FPy += r * ly;
    
    return TRUE;
}
