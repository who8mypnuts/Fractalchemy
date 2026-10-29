/*
    Fractalchemy formula library — translated from the JWildfire variation
        DCCarpet3DFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double dc_carpet3D_origin;
    double dc_carpet3D_color_a;
    double dc_carpet3D_color_b;
    double dc_carpet3D_color_c;
    double dc_carpet3D_color_d;
    double dc_carpet3D_color_e;
    double dc_carpet3D_color_f;
    double dc_carpet3D_stretch_x;
    double dc_carpet3D_stretch_y;
    double dc_carpet3D_scale_x;
    double dc_carpet3D_scale_y;
    double dc_carpet3D_scale_z;
    double dc_carpet3D_offset_z;
    double dc_carpet3D_reset_z;
    double dc_carpet3D_sides;
    double dc_carpet3D_H;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("dc_carpet3D");

APO_VARIABLES(
    VAR_REAL(dc_carpet3D_origin, 0.5),
    VAR_REAL(dc_carpet3D_color_a, 0.5),
    VAR_REAL(dc_carpet3D_color_b, 1),
    VAR_REAL(dc_carpet3D_color_c, 1),
    VAR_REAL(dc_carpet3D_color_d, 1),
    VAR_REAL(dc_carpet3D_color_e, 0.5),
    VAR_REAL(dc_carpet3D_color_f, 1),
    VAR_REAL(dc_carpet3D_stretch_x, 1),
    VAR_REAL(dc_carpet3D_stretch_y, 1),
    VAR_REAL(dc_carpet3D_scale_x, 1),
    VAR_REAL(dc_carpet3D_scale_y, 1),
    VAR_REAL(dc_carpet3D_scale_z, 1),
    VAR_REAL(dc_carpet3D_offset_z, 0),
    VAR_REAL(dc_carpet3D_reset_z, 0),
    VAR_REAL(dc_carpet3D_sides, 0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(dc_carpet3D_H) = 0.1 * VAR(dc_carpet3D_origin);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    int x0 = (random01() < 0.5) ? - 1 : 1;
    int y0 = (random01() > 0.5) ? - 1 : 1;
    double x = FTx + x0 * VAR(dc_carpet3D_stretch_x), y = FTy + y0 * VAR(dc_carpet3D_stretch_y);
    double x0_xor_y0 = (double)(x0 ^ y0);
    double hh = - VAR(dc_carpet3D_H) + (VAR(dc_carpet3D_color_b) - x0_xor_y0) * VAR(dc_carpet3D_H);
    FPx += VVAR * (TM(a) * x + TM(c) * y + TM(e)) * VAR(dc_carpet3D_scale_x);
    FPy += VVAR * (TM(b) * x + TM(d) * y + TM(f)) * VAR(dc_carpet3D_scale_y);
    TC = fmod(fabs(TC * VAR(dc_carpet3D_color_a) * (VAR(dc_carpet3D_color_c) + hh) + x0_xor_y0 * (VAR(dc_carpet3D_color_d) - hh) * VAR(dc_carpet3D_color_e)), VAR(dc_carpet3D_color_f));
    
    double dz = TC * VAR(dc_carpet3D_scale_z) + VAR(dc_carpet3D_offset_z);
    if(VAR(dc_carpet3D_reset_z) > 0) {
        FPz = dz;
    } else {
        FPz += dz;
        if(VAR(dc_carpet3D_sides) > 0) {
            FPz += dz * random01();
        } else {
            FPz += dz;
        }
    }
    return TRUE;
}
