/*
    Fractalchemy formula library — translated from the JWildfire variation
        R_CircleblurFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double r_circleblur_n;
    double r_circleblur_seed;
    double r_circleblur_dist;
    double r_circleblur_min;
    double r_circleblur_max;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("r_circleblur");

APO_VARIABLES(
    VAR_REAL(r_circleblur_n, 1),
    VAR_REAL(r_circleblur_seed, 0),
    VAR_REAL(r_circleblur_dist, 0.5),
    VAR_REAL(r_circleblur_min, 0.1),
    VAR_REAL(r_circleblur_max, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double rcn = fabs(VAR(r_circleblur_n));
    double angle = atan2(FTy, FTx);
    double rad = sqrt(sqr(FTx) + sqr(FTy));
    rad = fmod(rad, rcn);
    double by = sin(angle + rad);
    double bx = cos(angle + rad);
    by = round(by * rad);
    bx = round(bx * rad);
    double rad2 = sqrt(random01()) * 0.5;
    double angle2 = random01() * (2.0 * M_PI);
    double a1 = sin(bx * 127.1 + by * 311.7 + VAR(r_circleblur_seed)) * 43758.5453;
    a1 = a1 - trunc(a1);
    double a2 = sin(bx * 269.5 + by * 183.3 + VAR(r_circleblur_seed)) * 43758.5453;
    a2 = a2 - trunc(a2);
    double a3 = sin(by * 12.9898 + bx * 78.233 + VAR(r_circleblur_seed)) * 43758.5453;
    a3 = a3 - trunc(a3);
    a3 = a3 * (VAR(r_circleblur_max) - VAR(r_circleblur_min)) + VAR(r_circleblur_min);
    rad2 *= a3;
    by = by + rad2 * sin(angle2) + a1 * VAR(r_circleblur_dist);
    bx = bx + rad2 * cos(angle2) + a2 * VAR(r_circleblur_dist);
    FPx += VVAR * (bx);
    FPy += VVAR * (by);
    
    return TRUE;
}
