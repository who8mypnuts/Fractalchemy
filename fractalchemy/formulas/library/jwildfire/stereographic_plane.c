/*
    Fractalchemy formula library — translated from the JWildfire variation
        StereographicPlaneFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double stereographic_plane_scale;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("stereographic_plane");

APO_VARIABLES(
    VAR_REAL(stereographic_plane_scale, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double spp_lat = FTy * VAR(stereographic_plane_scale);
    double spp_lon = FTx * VAR(stereographic_plane_scale);
    double spp_cos_lat = cos(spp_lat);
    double spp_denom = max(1.0 - sin(spp_lat), 0.001);
    FPx += VVAR * spp_cos_lat * cos(spp_lon) / spp_denom;
    FPy += VVAR * spp_cos_lat * sin(spp_lon) / spp_denom;
    
    return TRUE;
}
