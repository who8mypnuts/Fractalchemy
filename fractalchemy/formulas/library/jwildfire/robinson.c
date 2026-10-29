/*
    Fractalchemy formula library — translated from the JWildfire variation
        RobinsonFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double robinson_scale;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("robinson");

APO_VARIABLES(
    VAR_REAL(robinson_scale, 1)
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
    double rbn_lat = clamp(FTy * VAR(robinson_scale), - 1.5707963267948966, 1.5707963267948966);
    double rbn_t = fabs(rbn_lat) / 1.5707963267948966;
    double rbn_xscale = 1.0 - 0.42 * rbn_t * rbn_t;
    double rbn_yscale = 1.0 + 0.12 * rbn_t;
    FPx += VVAR * FTx * max(rbn_xscale, 0.05) / VAR(robinson_scale);
    FPy += VVAR * rbn_lat * rbn_yscale / VAR(robinson_scale);
    
    return TRUE;
}
