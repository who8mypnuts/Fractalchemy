/*
    Fractalchemy formula library — translated from the JWildfire variation
        PreBlur3DFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

// keeps a private orbit between points (JWildfire fields updated per point): the statics below
#include "apoplugin.h"

APO_PLUGIN("pre_blur3D");

APO_NOVARIABLES;

static int gauss_N = 0;

int PluginVarPrepare(Variation* vp)
{
    double gauss_rnd[6];
    gauss_rnd[0] = random01();
    gauss_rnd[1] = random01();
    gauss_rnd[2] = random01();
    gauss_rnd[3] = random01();
    gauss_rnd[4] = random01();
    gauss_rnd[5] = random01();
    gauss_N = 0;
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double sina;
    double cosa;
    double sinb;
    double cosb;
    double gauss_rnd[6];
    double angle = random01() * 2 * M_PI;
    fsincos(angle, & sina, & cosa);
    double r = VVAR * (gauss_rnd[0] + gauss_rnd[1] + gauss_rnd[2] + gauss_rnd[3] + gauss_rnd[4] + gauss_rnd[5] - 3);
    gauss_rnd[gauss_N] = random01();
    gauss_N = (gauss_N + 1) & 5;
    angle = random01() * M_PI;
    fsincos(angle, & sinb, & cosb);
    FTx += r * sinb * cosa;
    FTy += r * sinb * sina;
    FTz += r * cosb;
    return TRUE;
}
