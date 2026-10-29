/*
    Fractalchemy formula library — translated from the JWildfire variation
        ParabolaFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double parabola_width;
    double parabola_height;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("parabola");

APO_VARIABLES(
    VAR_REAL(parabola_width, 1),
    VAR_REAL(parabola_height, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double r = (sqrt(FTx * FTx + FTy * FTy) + EPS);
    double sr = sin(r);
    double cr = cos(r);
    FPx += VAR(parabola_height) * VVAR * sr * sr * random01();
    FPy += VAR(parabola_width) * VVAR * cr * random01();
    
    return TRUE;
}
