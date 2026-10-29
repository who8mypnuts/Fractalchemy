/*
    Fractalchemy formula library — translated from the JWildfire variation
        CurlNoiseFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double curl_noise_freq;
    double curl_noise_strength;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("curl_noise");

APO_VARIABLES(
    VAR_REAL(curl_noise_freq, 2),
    VAR_REAL(curl_noise_strength, 0.3)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double dx = VAR(curl_noise_strength) * VAR(curl_noise_freq) * sin(VAR(curl_noise_freq) * FTx) * cos(VAR(curl_noise_freq) * FTy);
    double dy = - VAR(curl_noise_strength) * VAR(curl_noise_freq) * cos(VAR(curl_noise_freq) * FTx) * sin(VAR(curl_noise_freq) * FTy);
    FPx += VVAR * (FTx + dx);
    FPy += VVAR * (FTy + dy);
    
    return TRUE;
}
