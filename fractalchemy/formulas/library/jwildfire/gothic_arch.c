/*
    Fractalchemy formula library — translated from the JWildfire variation
        GothicArchFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double gothic_arch_height;
    double gothic_arch_sharpness;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("gothic_arch");

APO_VARIABLES(
    VAR_REAL(gothic_arch_height, 1),
    VAR_REAL(gothic_arch_sharpness, 2)
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
    double ga_h = max(fabs(VAR(gothic_arch_height)), 0.1);
    double ga_sharp = max(fabs(VAR(gothic_arch_sharpness)), 0.1);
    double ga_t = clamp(FTy / ga_h, - 2.0, 2.0);
    double ga_profile = max(1.0 - pow(fabs(ga_t), ga_sharp), 0.01);
    FPx += VVAR * FTx * ga_profile;
    FPy += VVAR * FTy;
    
    return TRUE;
}
