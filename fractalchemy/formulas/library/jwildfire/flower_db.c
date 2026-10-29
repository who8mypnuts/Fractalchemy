/*
    Fractalchemy formula library — translated from the JWildfire variation
        FlowerDbFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double flower_db_petals;
    double flower_db_petal_split;
    double flower_db_petal_spread;
    double flower_db_stem_thickness;
    double flower_db_stem_length;
    double flower_db_petal_fold_strength;
    double flower_db_petal_fold_radius;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("flower_db");

APO_VARIABLES(
    VAR_REAL(flower_db_petals, 6),
    VAR_REAL(flower_db_petal_split, 0),
    VAR_REAL(flower_db_petal_spread, 1),
    VAR_REAL(flower_db_stem_thickness, 1),
    VAR_REAL(flower_db_stem_length, 0),
    VAR_REAL(flower_db_petal_fold_strength, 0),
    VAR_REAL(flower_db_petal_fold_radius, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double r = VVAR * sqrt((FTx * FTx + FTy * FTy));
    double t = atan2(FTy, FTx);
    r = r * (fabs((VAR(flower_db_petal_spread) + sin(VAR(flower_db_petals) * t)) * cos(VAR(flower_db_petal_split) * VAR(flower_db_petals) * t)));
    FPx += sin(t) * r;
    FPy += cos(t) * r;
    FPz -= VAR(flower_db_stem_thickness) * ((2.0 / r) - 1.0);
    double rnew = sqrt((FPx * FPx) + (FPy * FPy));
    if(rnew > VAR(flower_db_petal_fold_radius)) {
        FPz += (rnew - VAR(flower_db_petal_fold_radius)) * VAR(flower_db_petal_fold_strength);
    }
    if((VAR(flower_db_stem_length) != 0) && (FPz <= (- 1 * VAR(flower_db_stem_length)))) {
        FPz = (- 1 * VAR(flower_db_stem_length));
    }
    return TRUE;
}
