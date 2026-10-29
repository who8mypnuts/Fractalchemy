/*
    Fractalchemy formula library — translated from the JWildfire variation
        ContourMapFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double contour_map_bands;
    double contour_map_pull;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("contour_map");

APO_VARIABLES(
    VAR_REAL(contour_map_bands, 5),
    VAR_REAL(contour_map_pull, 0.7)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double cm_r = sqrt(FTx * FTx + FTy * FTy);
    double cm_band_r = round(cm_r * VAR(contour_map_bands)) / VAR(contour_map_bands);
    double cm_nr = cm_r + VAR(contour_map_pull) * (cm_band_r - cm_r);
    double cm_scale = cm_r > 0.001 ? cm_nr / cm_r : 1.0;
    FPx += VVAR * FTx * cm_scale;
    FPy += VVAR * FTy * cm_scale;
    
    return TRUE;
}
