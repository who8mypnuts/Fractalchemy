/*
    Fractalchemy formula library — translated from the JWildfire variation
        DragonScaleFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double dragon_scale_freq;
    double dragon_scale_relief;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("dragon_scale");

APO_VARIABLES(
    VAR_REAL(dragon_scale_freq, 3),
    VAR_REAL(dragon_scale_relief, 0.4)
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
    double ds_freq = max(fabs(VAR(dragon_scale_freq)), 0.01);
    double ds_cx = round(FTx * ds_freq) / ds_freq;
    double ds_cy = round(FTy * ds_freq) / ds_freq;
    double ds_dx = FTx - ds_cx;
    double ds_dy = FTy - ds_cy;
    double ds_r2 = ds_dx * ds_dx + ds_dy * ds_dy;
    double ds_cell_r = 0.5 / ds_freq;
    double ds_bump = clamp(VAR(dragon_scale_relief) * (1.0 - ds_r2 / (ds_cell_r * ds_cell_r + 1e-6)), 0.0, 1.0);
    FPx += VVAR * (FTx + ds_bump * ds_dx);
    FPy += VVAR * (FTy + ds_bump * ds_dy);
    
    return TRUE;
}
