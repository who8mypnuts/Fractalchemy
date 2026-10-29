/*
    Fractalchemy formula library — translated from the JWildfire variation
        Spirograph3DFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double spirograph3D_a;
    double spirograph3D_b;
    double spirograph3D_c;
    double spirograph3D_tmin;
    double spirograph3D_tmax;
    double spirograph3D_width;
    int spirograph3D_mode;
    int spirograph3D_direct_color;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("spirograph3D");

APO_VARIABLES(
    VAR_REAL(spirograph3D_a, 1),
    VAR_REAL(spirograph3D_b, -0.3),
    VAR_REAL(spirograph3D_c, 0.4),
    VAR_REAL(spirograph3D_tmin, 0),
    VAR_REAL(spirograph3D_tmax, 1000),
    VAR_REAL(spirograph3D_width, 0),
    VAR_INTEGER(spirograph3D_mode, 0),
    VAR_INTEGER(spirograph3D_direct_color, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t = (VAR(spirograph3D_tmax) - VAR(spirograph3D_tmin)) * random01() + VAR(spirograph3D_tmin);
    double w1, w2, w3;
    switch(VAR(spirograph3D_mode)) {
        case 0 : w1 = w2 = w3 = VAR(spirograph3D_width) * random01() - VAR(spirograph3D_width) / 2;
        break;
        case 1 : w1 = VAR(spirograph3D_width) * random01() - VAR(spirograph3D_width) / 2;
        w2 = w1 * sin(36 * t + (2.0 * M_PI) / 3);
        w3 = w1 * sin(36 * t + 2 * (2.0 * M_PI) / 3);
        w1 = w1 * sin(36 * t);
        break;
        case 2 : w1 = VAR(spirograph3D_width) * random01() - VAR(spirograph3D_width) / 2;
        w2 = VAR(spirograph3D_width) * random01() - VAR(spirograph3D_width) / 2;
        w3 = VAR(spirograph3D_width) * random01() - VAR(spirograph3D_width) / 2;
        break;
        case 3 : w1 = VAR(spirograph3D_width) * (random01() + random01() + random01() + random01() - 2) / 2;
        w2 = VAR(spirograph3D_width) * (random01() + random01() + random01() + random01() - 2) / 2;
        w3 = VAR(spirograph3D_width) * (random01() + random01() + random01() + random01() - 2) / 2;
        break;
        case 4 : w1 = (random01() < 0.5) ? VAR(spirograph3D_width) : - VAR(spirograph3D_width);
        w2 = w3 = 0;
        break;
        default : w1 = w2 = w3 = 0;
    }
    double x1 = (VAR(spirograph3D_a) + VAR(spirograph3D_b)) * cos(t) - VAR(spirograph3D_c) * cos((VAR(spirograph3D_a) + VAR(spirograph3D_b)) / VAR(spirograph3D_b) * t);
    double y1 = (VAR(spirograph3D_a) + VAR(spirograph3D_b)) * sin(t) - VAR(spirograph3D_c) * sin((VAR(spirograph3D_a) + VAR(spirograph3D_b)) / VAR(spirograph3D_b) * t);
    double z1 = VAR(spirograph3D_c) * sin((VAR(spirograph3D_a) + VAR(spirograph3D_b)) / VAR(spirograph3D_b) * t);
    FPx += VVAR * (x1 + w1);
    FPy += VVAR * (y1 + w2);
    FPz += VVAR * (z1 + w3);
    if(VAR(spirograph3D_direct_color) != 0) {
        TC = fmod(t / (2.0 * M_PI), 1);
    }
    return TRUE;
}
