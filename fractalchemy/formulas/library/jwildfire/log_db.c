/*
    Fractalchemy formula library — translated from the JWildfire variation
        LogDbFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double log_db_base;
    double log_db_fix_period;
    double log_db__denom;
    double log_db__fixpe;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("log_db");

APO_VARIABLES(
    VAR_REAL(log_db_base, 1),
    VAR_REAL(log_db_fix_period, 1)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(log_db__denom) = 0.5;
    if(VAR(log_db_base) > 1e-20) VAR(log_db__denom) = VAR(log_db__denom) / log(2.71828182845905 * VAR(log_db_base));
    VAR(log_db__denom) *= VVAR;
    VAR(log_db__fixpe) = M_PI;
    if(VAR(log_db_fix_period) > 1e-20) VAR(log_db__fixpe) *= VAR(log_db_fix_period);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double fix_atan_period = 0;
    int adp;
    int i;
    for(i = 0;
    i < 7;
    i++) {
        adp = (int)(random01() *  10) - 5;
        if(abs(adp) >= 3) adp = 0;
        fix_atan_period += (double) adp;
    }
    fix_atan_period *= VAR(log_db__fixpe);
    FPx += VAR(log_db__denom) * log((FTx * FTx + FTy * FTy));
    FPy += VVAR * (atan2(FTy, FTx) + fix_atan_period);
    
    return TRUE;
}
