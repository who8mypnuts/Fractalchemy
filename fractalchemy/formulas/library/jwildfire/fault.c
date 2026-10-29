/*
    Fractalchemy formula library — translated from the JWildfire variation
        FaultFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double fault_angle;
    double fault_displacement;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("fault");

APO_VARIABLES(
    VAR_REAL(fault_angle, 30),
    VAR_REAL(fault_displacement, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double ft_angle = VAR(fault_angle) * M_PI / 180.0;
    double ft_nx = cos(ft_angle + M_PI * 0.5);
    double ft_ny = sin(ft_angle + M_PI * 0.5);
    double side = FTx * ft_nx + FTy * ft_ny;
    double side_sign = (side == 0.0) ? 0.0 : ((side < 0.0) ? - 1.0 : 1.0);
    double ft_cos = cos(ft_angle);
    double ft_sin = sin(ft_angle);
    FPx += VVAR * (FTx + side_sign * VAR(fault_displacement) * ft_cos);
    FPy += VVAR * (FTy + side_sign * VAR(fault_displacement) * ft_sin);
    
    return TRUE;
}
