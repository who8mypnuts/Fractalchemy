/*
    Fractalchemy formula library — translated from the JWildfire variation
        ToroidalFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double toroidal_major;
    double toroidal_minor;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("toroidal");

APO_VARIABLES(
    VAR_REAL(toroidal_major, 2),
    VAR_REAL(toroidal_minor, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double tor_x = (VAR(toroidal_major) + VAR(toroidal_minor) * cos(FTy)) * cos(FTx);
    double tor_y = (VAR(toroidal_major) + VAR(toroidal_minor) * cos(FTy)) * sin(FTx);
    FPx += VVAR * tor_x;
    FPy += VVAR * tor_y;
    
    return TRUE;
}
