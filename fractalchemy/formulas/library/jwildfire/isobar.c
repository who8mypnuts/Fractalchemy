/*
    Fractalchemy formula library — translated from the JWildfire variation
        IsobarFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double isobar_freq;
    double isobar_amp;
    double isobar_spin;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("isobar");

APO_VARIABLES(
    VAR_REAL(isobar_freq, 3),
    VAR_REAL(isobar_amp, 0.3),
    VAR_REAL(isobar_spin, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double r2 = FTx * FTx + FTy * FTy;
    double iso_r = sqrt(r2 + 1.0e-10);
    double iso_theta = atan2(FTy, FTx);
    double iso_band = sin(VAR(isobar_freq) * iso_r) * VAR(isobar_amp);
    double iso_nr = iso_r + iso_band;
    double iso_nt = iso_theta + VAR(isobar_spin) * iso_band;
    FPx += VVAR * iso_nr * cos(iso_nt);
    FPy += VVAR * iso_nr * sin(iso_nt);
    
    return TRUE;
}
