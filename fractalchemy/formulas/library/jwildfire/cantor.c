/*
    Fractalchemy formula library — translated from the JWildfire variation
        CantorFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double cantor_freq;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("cantor");

APO_VARIABLES(
    VAR_REAL(cantor_freq, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double fx = (FTx * VAR(cantor_freq)) % 3.0;
    if(fx < 0) fx += 3.0;
    double fy = (FTy * VAR(cantor_freq)) % 3.0;
    if(fy < 0) fy += 3.0;
    if(fx > 1.0 && fx < 2.0) fx = (fx < 1.5) ? 1.0 : 2.0;
    if(fy > 1.0 && fy < 2.0) fy = (fy < 1.5) ? 1.0 : 2.0;
    FPx += VVAR * fx / VAR(cantor_freq);
    FPy += VVAR * fy / VAR(cantor_freq);
    
    return TRUE;
}
