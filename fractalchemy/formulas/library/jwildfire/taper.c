/*
    Fractalchemy formula library — translated from the JWildfire variation
        TaperFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double taper_strength;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("taper");

APO_VARIABLES(
    VAR_REAL(taper_strength, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double tp_scale = max(1.0 - VAR(taper_strength) * fabs(FTy), 0.01);
    FPx += VVAR * FTx * tp_scale;
    FPy += VVAR * FTy;
    
    return TRUE;
}
