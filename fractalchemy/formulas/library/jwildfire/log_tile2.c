/*
    Fractalchemy formula library — translated from the JWildfire variation
        LogTile2Func.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double log_tile2_spreadx;
    double log_tile2_spready;
    double log_tile2_spreadz;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("log_tile2");

APO_VARIABLES(
    VAR_REAL(log_tile2_spreadx, 2),
    VAR_REAL(log_tile2_spready, 2),
    VAR_REAL(log_tile2_spreadz, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double spreadx = - VAR(log_tile2_spreadx);
    if(random01() < 0.5) spreadx = VAR(log_tile2_spreadx);
    double spready = - VAR(log_tile2_spready);
    if(random01() < 0.5) spready = VAR(log_tile2_spready);
    double spreadz = - VAR(log_tile2_spreadz);
    if(random01() < 0.5) spreadz = VAR(log_tile2_spreadz);
    FPx += VVAR * (FTx + spreadx * round(log(random01())));
    FPy += VVAR * (FTy + spready * round(log(random01())));
    FPz += VVAR * (FTz + spreadz * round(log(random01())));
    return TRUE;
}
