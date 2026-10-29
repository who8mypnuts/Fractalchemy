/*
    Fractalchemy formula library — translated from the JWildfire variation
        LineFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double line_delta;
    double line_phi;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("line");

APO_VARIABLES(
    VAR_REAL(line_delta, 0),
    VAR_REAL(line_phi, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double ux = cos(VAR(line_delta) * M_PI) * cos(VAR(line_phi) * M_PI);
    double uy = sin(VAR(line_delta) * M_PI) * cos(VAR(line_phi) * M_PI);
    double uz = sin(VAR(line_phi) * M_PI);
    double r = sqrt(ux * ux + uy * uy + uz * uz);
    ux /= r;
    uy /= r;
    uz /= r;
    double rand = random01() * VVAR;
    FPx += ux * rand;
    FPy += uy * rand;
    FPz += uz * rand;
    return TRUE;
}
