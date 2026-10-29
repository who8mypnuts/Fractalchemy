/*
    Fractalchemy formula library — translated from the JWildfire variation
        KarmanVortexFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double karman_vortex_freq;
    double karman_vortex_strength;
    double karman_vortex_sep;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("karman_vortex");

APO_VARIABLES(
    VAR_REAL(karman_vortex_freq, 2),
    VAR_REAL(karman_vortex_strength, 0.3),
    VAR_REAL(karman_vortex_sep, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double kv_freq = max(fabs(VAR(karman_vortex_freq)), 0.01);
    double kv_xi = round(FTx * kv_freq);
    double kv_parity = kv_xi % 2.0;
    if(kv_parity < 0) kv_parity += 2.0;
    double kv_vcx = kv_xi / kv_freq;
    double kv_vcy = VAR(karman_vortex_sep) * 0.5 * (2.0 * kv_parity - 1.0);
    double kv_dx = FTx - kv_vcx;
    double kv_dy = FTy - kv_vcy;
    double kv_r2 = kv_dx * kv_dx + kv_dy * kv_dy + 1e-4;
    double kv_spin = VAR(karman_vortex_strength) * (2.0 * kv_parity - 1.0) / kv_r2;
    FPx += VVAR * (FTx + kv_spin * (- kv_dy));
    FPy += VVAR * (FTy + kv_spin * kv_dx);
    
    return TRUE;
}
