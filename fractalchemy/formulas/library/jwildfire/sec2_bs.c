/*
    Fractalchemy formula library — translated from the JWildfire variation
        Sec2_BSFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double sec2_bs_x1;
    double sec2_bs_x2;
    double sec2_bs_y1;
    double sec2_bs_y2;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("sec2_bs");

APO_VARIABLES(
    VAR_REAL(sec2_bs_x1, 1.25),
    VAR_REAL(sec2_bs_x2, 0.75),
    VAR_REAL(sec2_bs_y1, 1.5),
    VAR_REAL(sec2_bs_y2, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double secsin = sin(FTx * VAR(sec2_bs_x1));
    double seccos = cos(FTx * VAR(sec2_bs_x2));
    double secsinh = sinh(FTy * VAR(sec2_bs_y1));
    double seccosh = cosh(FTy * VAR(sec2_bs_y2));
    double d = (cos(2.0 * FTx) + cosh(2.0 * FTy));
    if(d == 0) {
        return;
    }
    double secden = 2.0 / d;
    FPx += VVAR * secden * seccos * seccosh;
    FPy += VVAR * secden * secsin * secsinh;
    
    return TRUE;
}
