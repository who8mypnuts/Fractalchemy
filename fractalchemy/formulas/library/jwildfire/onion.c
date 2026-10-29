/*
    Fractalchemy formula library — translated from the JWildfire variation
        OnionFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double onion_centre_x;
    double onion_centre_y;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("onion");

APO_VARIABLES(
    VAR_REAL(onion_centre_x, 0),
    VAR_REAL(onion_centre_y, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double r0 = VVAR;
    double x0 = FTx;
    double y0 = FTy;
    if(r0 == 0.0) {
        r0 = 1.0;
    }
    x0 -= VAR(onion_centre_x);
    y0 -= VAR(onion_centre_y);
    double d0 = (x0 * x0) + (y0 * y0);
    double dr = sqrt(d0);
    double x1 = 0.0;
    double y1 = 0.0;
    double z1 = 0.0;
    if(d0 <= r0 * r0) {
        z1 -= sqrt((r0 * r0) - d0);
        x1 = x0;
        y1 = y0;
    } else if(2 * r0 - dr > r0 / 1.41421356) {
        x1 = (2 * r0 - dr) * x0 / dr;
        y1 = (2 * r0 - dr) * y0 / dr;
        z1 = sqrt(r0 * r0 - ((x1 * x1) + (y1 * y1)));
    } else {
        z1 = exp(dr - r0 - (r0 - r0 / 1.414213569)) - 1.0 + (r0 / 1.414213569);
        x1 = (2 * r0 - dr) * x0 / dr;
        y1 = (2 * r0 - dr) * y0 / dr;
    }
    x1 += VAR(onion_centre_x);
    y1 += VAR(onion_centre_y);
    FPx += x1;
    FPy += y1;
    FPz += z1 + FTz;
    return TRUE;
}
