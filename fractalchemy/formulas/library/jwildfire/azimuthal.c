/*
    Fractalchemy formula library — translated from the JWildfire variation
        AzimuthalFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double azimuthal_scale;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("azimuthal");

APO_VARIABLES(
    VAR_REAL(azimuthal_scale, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double az_r = sqrt(FTx * FTx + FTy * FTy);
    double az_theta = atan2(FTy, FTx);
    double az_nr = az_r > 0.001 ? sin(az_r * VAR(azimuthal_scale)) / VAR(azimuthal_scale) : az_r;
    FPx += VVAR * az_nr * cos(az_theta);
    FPy += VVAR * az_nr * sin(az_theta);
    
    return TRUE;
}
