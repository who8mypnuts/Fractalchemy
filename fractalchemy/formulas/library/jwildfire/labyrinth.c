/*
    Fractalchemy formula library — translated from the JWildfire variation
        LabyrinthFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double labyrinth_scale;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("labyrinth");

APO_VARIABLES(
    VAR_REAL(labyrinth_scale, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double lb_scale = max(fabs(VAR(labyrinth_scale)), 0.01);
    double lb_ri = floor(FTx / lb_scale + 0.5);
    double lb_ci = floor(FTy / lb_scale + 0.5);
    double lb_lx = FTx - lb_ri * lb_scale;
    double lb_ly = FTy - lb_ci * lb_scale;
    double row_mod = fabs(lb_ci) % 2.0;
    double col_mod = fabs(lb_ri) % 2.0;
    double lb_fx = row_mod > 0.5 ? - lb_lx : lb_lx;
    double lb_fy = col_mod > 0.5 ? - lb_ly : lb_ly;
    FPx += VVAR * (lb_ri * lb_scale + lb_fx);
    FPy += VVAR * (lb_ci * lb_scale + lb_fy);
    
    return TRUE;
}
