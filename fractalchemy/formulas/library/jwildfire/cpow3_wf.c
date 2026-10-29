/*
    Fractalchemy formula library — translated from the JWildfire variation
        CPow3WFFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double cpow3_wf_r;
    double cpow3_wf_a;
    double cpow3_wf_divisor;
    double cpow3_wf_spread;
    double cpow3_wf_discrete_spread;
    double cpow3_wf_spread2;
    double cpow3_wf_offset2;
    double cpow3_wf_c;
    double cpow3_wf_d;
    double cpow3_wf_half_c;
    double cpow3_wf_half_d;
    double cpow3_wf_ang;
    double cpow3_wf_inv_spread;
    double cpow3_wf_full_spread;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("cpow3_wf");

APO_VARIABLES(
    VAR_REAL(cpow3_wf_r, 1),
    VAR_REAL(cpow3_wf_a, 0.1),
    VAR_REAL(cpow3_wf_divisor, 1),
    VAR_REAL(cpow3_wf_spread, 1),
    VAR_REAL(cpow3_wf_discrete_spread, 1),
    VAR_REAL(cpow3_wf_spread2, 0),
    VAR_REAL(cpow3_wf_offset2, 1)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(cpow3_wf_ang) = 2.0 * M_PI / VAR(cpow3_wf_divisor);
    VAR(cpow3_wf_c) = VAR(cpow3_wf_r) * cos(M_PI / 2 * VAR(cpow3_wf_a)) / VAR(cpow3_wf_divisor);
    VAR(cpow3_wf_d) = VAR(cpow3_wf_r) * sin(M_PI / 2 * VAR(cpow3_wf_a)) / VAR(cpow3_wf_divisor);
    VAR(cpow3_wf_half_c) = VAR(cpow3_wf_c) / 2;
    VAR(cpow3_wf_half_d) = VAR(cpow3_wf_d) / 2;
    VAR(cpow3_wf_inv_spread) = 0.5 / VAR(cpow3_wf_spread);
    VAR(cpow3_wf_full_spread) = 2 * M_PI * VAR(cpow3_wf_spread);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double ai = atan2(FTy, FTx);
    double n = random01() * VAR(cpow3_wf_spread);
    if(VAR(cpow3_wf_discrete_spread) >= 1.0) {
        n = (int) n;
    }
    if(ai < 0) {
        n++;
    }
    ai += 2 * M_PI * n;
    if(cos(ai * VAR(cpow3_wf_inv_spread)) < (random01() * 2.0 - 1.0)) {
        ai -= VAR(cpow3_wf_full_spread);
    }
    double lnr2 = log((FTx * FTx + FTy * FTy));
    double ri = VVAR * exp(VAR(cpow3_wf_half_c) * lnr2 - VAR(cpow3_wf_d) * ai);
    double ang2 = VAR(cpow3_wf_c) * ai * VAR(cpow3_wf_half_d) * lnr2 * VAR(cpow3_wf_ang) * (random01() * VAR(cpow3_wf_spread2) + VAR(cpow3_wf_offset2));
    FPx += ri * cos(ang2);
    FPy += ri * sin(ang2);
    
    return TRUE;
}
