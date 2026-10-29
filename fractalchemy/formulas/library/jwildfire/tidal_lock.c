/*
    Fractalchemy formula library — translated from the JWildfire variation
        TidalLockFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double tidal_lock_ratio;
    double tidal_lock_ecc;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("tidal_lock");

APO_VARIABLES(
    VAR_REAL(tidal_lock_ratio, 1),
    VAR_REAL(tidal_lock_ecc, 0.3)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double tl_r = sqrt(FTx * FTx + FTy * FTy);
    double tl_a = atan2(FTy, FTx);
    double tl_new_a = tl_a * VAR(tidal_lock_ratio) + VAR(tidal_lock_ecc) * sin(2.0 * tl_a);
    FPx += VVAR * tl_r * cos(tl_new_a);
    FPy += VVAR * tl_r * sin(tl_new_a);
    
    return TRUE;
}
