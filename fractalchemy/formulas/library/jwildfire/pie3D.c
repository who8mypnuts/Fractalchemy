/*
    Fractalchemy formula library — translated from the JWildfire variation
        Pie3DFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double pie3D_slices;
    double pie3D_rotation;
    double pie3D_thickness;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("pie3D");

APO_VARIABLES(
    VAR_REAL(pie3D_slices, 7),
    VAR_REAL(pie3D_rotation, 0),
    VAR_REAL(pie3D_thickness, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    int sl = (int)(random01() * VAR(pie3D_slices) + 0.5);
    double a = VAR(pie3D_rotation) + 2.0 * M_PI * (sl + random01() * VAR(pie3D_thickness)) / VAR(pie3D_slices);
    double r = VVAR * random01();
    double sina = sin(a);
    double cosa = cos(a);
    FPx += r * cosa;
    FPy += r * sina;
    FPz += r * sin(r);
    return TRUE;
}
