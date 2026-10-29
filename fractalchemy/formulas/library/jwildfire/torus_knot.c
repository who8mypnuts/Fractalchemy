/*
    Fractalchemy formula library — translated from the JWildfire variation
        TorusKnotFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double torus_knot_p;
    double torus_knot_q;
    double torus_knot_r_big;
    double torus_knot_r_small;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("torus_knot");

APO_VARIABLES(
    VAR_REAL(torus_knot_p, 2),
    VAR_REAL(torus_knot_q, 3),
    VAR_REAL(torus_knot_r_big, 1),
    VAR_REAL(torus_knot_r_small, 0.3)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t = atan2(FTy, FTx);
    double outer = VAR(torus_knot_r_big) + VAR(torus_knot_r_small) * cos(VAR(torus_knot_q) * t);
    FPx += VVAR * outer * cos(VAR(torus_knot_p) * t);
    FPy += VVAR * outer * sin(VAR(torus_knot_p) * t);
    
    return TRUE;
}
