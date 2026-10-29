/*
    Fractalchemy formula library — translated from the JWildfire variation
        HammerFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double hammer_scale;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("hammer");

APO_VARIABLES(
    VAR_REAL(hammer_scale, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double hm_lat = FTy * VAR(hammer_scale);
    double hm_lon = FTx * VAR(hammer_scale);
    double hm_cos_lat = cos(hm_lat);
    double hm_d = sqrt(1.0 + hm_cos_lat * cos(hm_lon * 0.5)) + 0.001;
    FPx += VVAR * 2.82842712474619 * hm_cos_lat * sin(hm_lon * 0.5) / hm_d;
    FPy += VVAR * 1.414213562373095 * sin(hm_lat) / hm_d;
    
    return TRUE;
}
