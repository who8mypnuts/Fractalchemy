/*
    Fractalchemy formula library — translated from the JWildfire variation
        QuiltFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double quilt_scale;
    double quilt_puff;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("quilt");

APO_VARIABLES(
    VAR_REAL(quilt_scale, 3),
    VAR_REAL(quilt_puff, 0.3)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double qt_cx = FTx * VAR(quilt_scale);
    double qt_cy = FTy * VAR(quilt_scale);
    double qt_col = round(qt_cx);
    double qt_row = round(qt_cy);
    double qt_lx = qt_cx - qt_col;
    double qt_ly = qt_cy - qt_row;
    double qt_dist = sqrt(qt_lx * qt_lx + qt_ly * qt_ly);
    double qt_bulge = VAR(quilt_puff) * (1.0 - qt_dist * 2.0);
    FPx += VVAR * (qt_col + qt_lx * (1.0 - qt_bulge)) / VAR(quilt_scale);
    FPy += VVAR * (qt_row + qt_ly * (1.0 - qt_bulge)) / VAR(quilt_scale);
    
    return TRUE;
}
