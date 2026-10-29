/*
    Fractalchemy formula library — translated from the JWildfire variation
        MapleLeafFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double maple_leaf_filled;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("maple_leaf");

APO_VARIABLES(
    VAR_REAL(maple_leaf_filled, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t = atan2(FTx, FTy) - M_PI_2;
    double r = (VAR(maple_leaf_filled) > 0 && VAR(maple_leaf_filled) > random01()) ? VVAR * random01() : VVAR;
    double lx = (1.0 + pow((cos(6.0 * t)), 2.0) + 1.0 / 5.0 * pow((cos(6.0 * t) * cos(24.0 * t)), 10.0) + (1 / 4 * pow((cos(30.0 * t)), 2) + 1.0 / 9.0 * pow((cos(30.0 * t)), 12.0)) * (1.0 - pow((sin(6.0 * t)), 10.0))) * (sin(2.0 * t)) * (1.0 - pow((cos(t)), 4.0)) * (1.0 - pow((cos(t)), 10.0) * pow((cos(3.0 * t)), 2.0));
    double ly = 21.0 / 20.0 * cos(2.0 * t) * (1.0 - pow((cos(t)), 4.0) + 1.0 / 2.0 * pow((cos(t) * cos(3.0 * t)), 10.0)) * (1.0 + pow((cos(6.0 * t)), 2.0) + 1.0 / 5.0 * pow((cos(6.0 * t) * cos(18.0 * t)), 10.0) + (1.0 / 4.0 * pow((cos(30.0 * t)), 4) + 1.0 / 10.0 * pow((cos(30.0 * t)), 12.0)) * (1.0 - pow((cos(t)), 10.0) * pow((cos(3.0 * t)), 2.0)) * (1.0 - pow((sin(6.0 * t)), 10.0)));
    FPx += r * lx;
    FPy += r * ly;
    
    return TRUE;
}
