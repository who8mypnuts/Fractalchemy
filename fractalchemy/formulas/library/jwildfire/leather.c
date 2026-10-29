/*
    Fractalchemy formula library — translated from the JWildfire variation
        LeatherFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double leather_scale;
    double leather_rough;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("leather");

APO_VARIABLES(
    VAR_REAL(leather_scale, 2),
    VAR_REAL(leather_rough, 0.3)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double lt_scale = max(fabs(VAR(leather_scale)), 0.01);
    double lt_coarse = VAR(leather_rough) * sin(lt_scale * FTx) * cos(lt_scale * FTy);
    double lt_fine = VAR(leather_rough) * 0.3 * sin(lt_scale * 3.0 * FTy) * cos(lt_scale * 3.0 * FTx);
    FPx += VVAR * (FTx + lt_coarse);
    FPy += VVAR * (FTy + lt_fine);
    
    return TRUE;
}
