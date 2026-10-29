/*
    Fractalchemy formula library — translated from the JWildfire variation
        MirrorRotateFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double mirror_rotate_angle;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("mirror_rotate");

APO_VARIABLES(
    VAR_REAL(mirror_rotate_angle, 45)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double mr_angle = VAR(mirror_rotate_angle) * 0.017453292519943295;
    double c2 = cos(2.0 * mr_angle);
    double s2 = sin(2.0 * mr_angle);
    double nx = FTx * c2 + FTy * s2;
    double ny = FTx * s2 - FTy * c2;
    FPx += VVAR * nx;
    FPy += VVAR * ny;
    
    return TRUE;
}
