/*
    Fractalchemy formula library — translated from the JWildfire variation
        LissajousFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double lissajous_tmin;
    double lissajous_tmax;
    double lissajous_a;
    double lissajous_b;
    double lissajous_c;
    double lissajous_d;
    double lissajous_e;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("lissajous");

APO_VARIABLES(
    VAR_REAL(lissajous_tmin, -3.14159),
    VAR_REAL(lissajous_tmax, 3.14159),
    VAR_REAL(lissajous_a, 3),
    VAR_REAL(lissajous_b, 2),
    VAR_REAL(lissajous_c, 0),
    VAR_REAL(lissajous_d, 0),
    VAR_REAL(lissajous_e, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t = (VAR(lissajous_tmax) - VAR(lissajous_tmin)) * random01() + VAR(lissajous_tmin);
    double y = random01() - 0.5;
    double x1 = sin(VAR(lissajous_a) * t + VAR(lissajous_d));
    double y1 = sin(VAR(lissajous_b) * t);
    FPx += VVAR * (x1 + VAR(lissajous_c) * t + VAR(lissajous_e) * y);
    FPy += VVAR * (y1 + VAR(lissajous_c) * t + VAR(lissajous_e) * y);
    
    return TRUE;
}
