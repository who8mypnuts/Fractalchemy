/*
    Fractalchemy formula library — translated from the JWildfire variation
        MushroomFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double mushroom_cap_r;
    double mushroom_cap_w;
    double mushroom_stalk_w;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("mushroom");

APO_VARIABLES(
    VAR_REAL(mushroom_cap_r, 0.5),
    VAR_REAL(mushroom_cap_w, 2),
    VAR_REAL(mushroom_stalk_w, 0.3)
);

double clamp(double value, double min, double max)
{
    return max(min, min(max, value));
}

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double mu_cr = max(fabs(VAR(mushroom_cap_r)), 0.01);
    double mu_cw = max(fabs(VAR(mushroom_cap_w)), 0.01);
    double mu_sw = clamp(VAR(mushroom_stalk_w), 0.05, 2.0);
    double mu_above = 0.5 + 0.5 * tanh(FTy / (mu_cr * 0.3));
    double mu_cap_env = exp(- (FTy - mu_cr * 0.5) * (FTy - mu_cr * 0.5) / (mu_cr * mu_cr * 0.5 + 1e-6));
    double mu_scale = mu_sw + (mu_cw - mu_sw) * mu_above + mu_cap_env * 0.4;
    FPx = VVAR * FTx * mu_scale;
    FPy = VVAR * FTy;
    
    return TRUE;
}
