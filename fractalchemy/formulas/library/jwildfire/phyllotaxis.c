/*
    Fractalchemy formula library — translated from the JWildfire variation
        PhyllotaxisFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double phyllotaxis_spread;
    double phyllotaxis_angle_step;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("phyllotaxis");

APO_VARIABLES(
    VAR_REAL(phyllotaxis_spread, 0.1),
    VAR_REAL(phyllotaxis_angle_step, 137.508)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double ph_spread = max(fabs(VAR(phyllotaxis_spread)), 1e-4);
    double ph_step = VAR(phyllotaxis_angle_step) * M_PI / 180.0;
    double r = sqrt(FTx * FTx + FTy * FTy);
    double index = r / ph_spread;
    double theta = index * ph_step;
    double new_r = sqrt(index) * ph_spread;
    FPx += VVAR * new_r * cos(theta);
    FPy += VVAR * new_r * sin(theta);
    
    return TRUE;
}
