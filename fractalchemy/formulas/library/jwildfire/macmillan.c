/*
    Fractalchemy formula library — translated from the JWildfire variation
        MacMillanFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

// keeps a private orbit between points (JWildfire fields updated per point): the statics below
typedef struct {
    double macmillan_a;
    double macmillan_b;
    double macmillan_N;
    double macmillan_startx;
    double macmillan_starty;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("macmillan");

APO_VARIABLES(
    VAR_REAL(macmillan_a, 1.6),
    VAR_REAL(macmillan_b, 0.4),
    VAR_REAL(macmillan_startx, 0.1),
    VAR_REAL(macmillan_starty, 0.1)
);

static double xa = 0;
static double x = 0;
static double y = 0;

int PluginVarPrepare(Variation* vp)
{
    xa = VAR(macmillan_startx);
    y = VAR(macmillan_starty);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    x = y;
    y = - xa + 2. * VAR(macmillan_a) * (y / (1 + y * y)) + VAR(macmillan_b) * y;
    xa = x;
    x = y;
    y = - xa + 2 * VAR(macmillan_a) * (y / (1 + y * y)) + VAR(macmillan_b) * y;
    FPx += VVAR * x;
    FPy += VVAR * y;
    xa = x;
    return TRUE;
}
