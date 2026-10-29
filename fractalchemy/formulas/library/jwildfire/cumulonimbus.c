/*
    Fractalchemy formula library — translated from the JWildfire variation
        CumulonimbusFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double cumulonimbus_height;
    double cumulonimbus_spread;
    double cumulonimbus_turb;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("cumulonimbus");

APO_VARIABLES(
    VAR_REAL(cumulonimbus_height, 1),
    VAR_REAL(cumulonimbus_spread, 0.5),
    VAR_REAL(cumulonimbus_turb, 0.15)
);

double clamp(double value, double min, double max)
{
    return max(min, min(max, value));
}

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double cb_h = max(fabs(VAR(cumulonimbus_height)), 0.1);
    double cb_t = clamp(FTy / cb_h, - 1.5, 1.5);
    double cb_anvil = VAR(cumulonimbus_spread) * cb_t * fabs(cb_t);
    double cb_shake = VAR(cumulonimbus_turb) * sin(FTy * 4.1 + fabs(FTx) * 2.3);
    FPx += VVAR * (FTx + cb_anvil + cb_shake * (1.0 - fabs(cb_t) * 0.5));
    FPy += VVAR * (FTy * (1.0 + 0.5 * fabs(cb_t)));
    
    return TRUE;
}
