/*
    Fractalchemy formula library — translated from the JWildfire variation
        SinusoidalProjFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double sinusoidal_proj_scale;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("sinusoidal_proj");

APO_VARIABLES(
    VAR_REAL(sinusoidal_proj_scale, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double sip_lat = FTy * VAR(sinusoidal_proj_scale);
    FPx += VVAR * FTx * cos(sip_lat);
    FPy += VVAR * FTy;
    
    return TRUE;
}
