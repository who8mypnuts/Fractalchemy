/*
    Fractalchemy formula library — translated from the JWildfire variation
        CoagulationFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double coagulation_freq;
    double coagulation_pull;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("coagulation");

APO_VARIABLES(
    VAR_REAL(coagulation_freq, 3),
    VAR_REAL(coagulation_pull, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double cg_cx = round(FTx * VAR(coagulation_freq)) / VAR(coagulation_freq);
    double cg_cy = round(FTy * VAR(coagulation_freq)) / VAR(coagulation_freq);
    double cg_dx = cg_cx - FTx;
    double cg_dy = cg_cy - FTy;
    FPx += VVAR * (FTx + VAR(coagulation_pull) * cg_dx);
    FPy += VVAR * (FTy + VAR(coagulation_pull) * cg_dy);
    
    return TRUE;
}
