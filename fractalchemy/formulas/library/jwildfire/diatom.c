/*
    Fractalchemy formula library — translated from the JWildfire variation
        DiatomFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    int diatom_spokes;
    double diatom_amplitude;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("diatom");

APO_VARIABLES(
    VAR_INTEGER(diatom_spokes, 8),
    VAR_REAL(diatom_amplitude, 0.3)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double r2 = FTx * FTx + FTy * FTy;
    double dt_r = sqrt(r2 + 1.0e-10);
    double dt_theta = atan2(FTy, FTx);
    double dt_radial = 1.0 + VAR(diatom_amplitude) * cos((double) VAR(diatom_spokes) * dt_theta);
    double dt_nr = dt_r * dt_radial;
    FPx += VVAR * dt_nr * cos(dt_theta);
    FPy += VVAR * dt_nr * sin(dt_theta);
    
    return TRUE;
}
