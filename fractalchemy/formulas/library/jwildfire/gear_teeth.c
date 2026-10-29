/*
    Fractalchemy formula library — translated from the JWildfire variation
        GearTeethFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double gear_teeth_teeth;
    double gear_teeth_depth;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("gear_teeth");

APO_VARIABLES(
    VAR_REAL(gear_teeth_teeth, 12),
    VAR_REAL(gear_teeth_depth, 0.3)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double gt_a = atan2(FTy, FTx);
    double gt_r = sqrt(FTx * FTx + FTy * FTy);
    double gt_tooth = 0.5 * (1.0 + cos(VAR(gear_teeth_teeth) * gt_a));
    double gt_rmod = gt_r + VAR(gear_teeth_depth) * gt_tooth;
    FPx += VVAR * gt_rmod * cos(gt_a);
    FPy += VVAR * gt_rmod * sin(gt_a);
    
    return TRUE;
}
