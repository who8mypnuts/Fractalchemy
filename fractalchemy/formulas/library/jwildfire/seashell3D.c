/*
    Fractalchemy formula library — translated from the JWildfire variation
        SeaShell3DFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double seashell3D_final_radius;
    double seashell3D_height;
    double seashell3D_inner_radius;
    int seashell3D_nSpirals;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("seashell3D");

APO_VARIABLES(
    VAR_REAL(seashell3D_final_radius, 0.25),
    VAR_REAL(seashell3D_height, 3.5),
    VAR_REAL(seashell3D_inner_radius, 0.4),
    VAR_INTEGER(seashell3D_nSpirals, 3)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t;
    double s;
    t = M_2PI * random01();
    s = M_2PI * random01();
    double x = VAR(seashell3D_final_radius) * (1 - t / M_2PI) * cos(VAR(seashell3D_nSpirals) * t) * (1.0 + cos(s)) + VAR(seashell3D_inner_radius) * cos(VAR(seashell3D_nSpirals) * t);
    double y = VAR(seashell3D_final_radius) * (1 - t / M_2PI) * sin(VAR(seashell3D_nSpirals) * t) * (1.0 + cos(s)) + VAR(seashell3D_inner_radius) * sin(VAR(seashell3D_nSpirals) * t);
    double z = VAR(seashell3D_height) * t / M_2PI + VAR(seashell3D_final_radius) * (1 - t / M_2PI) * sin(s);
    FPx += x * VVAR;
    FPy += y * VVAR;
    FPz += z * VVAR;
    return TRUE;
}
