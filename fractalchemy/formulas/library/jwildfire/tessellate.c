/*
    Fractalchemy formula library — translated from the JWildfire variation
        TessellateFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double tessellate_scale;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("tessellate");

APO_VARIABLES(
    VAR_REAL(tessellate_scale, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double ts_s = max(fabs(VAR(tessellate_scale)), 0.01);
    double ts_nx = (FTx + ts_s * 0.5) % ts_s;
    if(ts_nx < 0.0) ts_nx += ts_s;
    ts_nx -= ts_s * 0.5;
    double ts_ny = (FTy + ts_s * 0.5) % ts_s;
    if(ts_ny < 0.0) ts_ny += ts_s;
    ts_ny -= ts_s * 0.5;
    FPx += VVAR * ts_nx;
    FPy += VVAR * ts_ny;
    
    return TRUE;
}
