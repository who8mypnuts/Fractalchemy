/*
    Fractalchemy formula library — translated from the JWildfire variation
        SphHarmonicFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    int sph_harmonic_l;
    int sph_harmonic_m;
    double sph_harmonic_strength;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("sph_harmonic");

APO_VARIABLES(
    VAR_INTEGER(sph_harmonic_l, 2),
    VAR_INTEGER(sph_harmonic_m, 1),
    VAR_REAL(sph_harmonic_strength, 0.3)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double sh_theta = atan2(FTy, FTx);
    double sh_r = sqrt(FTx * FTx + FTy * FTy);
    double sh_harm = cos((double) VAR(sph_harmonic_l) * sh_theta) * cos((double) VAR(sph_harmonic_m) * sh_theta);
    double sh_nr = sh_r * (1.0 + VAR(sph_harmonic_strength) * sh_harm);
    FPx += VVAR * sh_nr * cos(sh_theta);
    FPy += VVAR * sh_nr * sin(sh_theta);
    
    return TRUE;
}
