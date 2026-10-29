/*
    Fractalchemy formula library — translated from the JWildfire variation
        PleatFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double pleat_width;
    double pleat_depth;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("pleat");

APO_VARIABLES(
    VAR_REAL(pleat_width, 0.5),
    VAR_REAL(pleat_depth, 0.3)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double pl_width = max(fabs(VAR(pleat_width)), 0.01);
    double pl_cell = floor(FTx / pl_width);
    double pl_lx = FTx / pl_width - pl_cell;
    double pl_crease = VAR(pleat_depth) * (1.0 - fabs(2.0 * pl_lx - 1.0));
    double row_mod = pl_cell % 2.0;
    if(row_mod < 0) row_mod += 2.0;
    double pl_dir = row_mod > 0.5 ? 1.0 : - 1.0;
    FPx += VVAR * FTx;
    FPy += VVAR * (FTy + pl_crease * pl_dir);
    
    return TRUE;
}
