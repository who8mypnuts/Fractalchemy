/*
    Fractalchemy formula library — translated from the JWildfire variation
        FractalZoomFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double fractal_zoom_zoom;
    double fractal_zoom_angle;
    int fractal_zoom_iters;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("fractal_zoom");

APO_VARIABLES(
    VAR_REAL(fractal_zoom_zoom, 2),
    VAR_REAL(fractal_zoom_angle, 0.5),
    VAR_INTEGER(fractal_zoom_iters, 3)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double fz_x = FTx;
    double fz_y = FTy;
    double fz_cs = cos(VAR(fractal_zoom_angle));
    double fz_sn = sin(VAR(fractal_zoom_angle));
    for(int i = 0;
    i < VAR(fractal_zoom_iters);
    i++) {
        double fz_nx = fz_x * fz_cs - fz_y * fz_sn;
        double fz_ny = fz_x * fz_sn + fz_y * fz_cs;
        fz_x = fz_nx * VAR(fractal_zoom_zoom);
        fz_y = fz_ny * VAR(fractal_zoom_zoom);
    }
    FPx += VVAR * fz_x;
    FPy += VVAR * fz_y;
    
    return TRUE;
}
