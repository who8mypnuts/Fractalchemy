/*
    Fractalchemy formula library — translated from the JWildfire variation
        PostBenesiCropFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    int post_benesi_crop_iterations;
    double post_benesi_crop_bailout;
    double post_benesi_crop_scaleX;
    double post_benesi_crop_scaleY;
    double post_benesi_crop_ScaleZ;
    double post_benesi_crop_color;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("post_benesi_crop");

APO_VARIABLES(
    VAR_INTEGER(post_benesi_crop_iterations, 12),
    VAR_REAL(post_benesi_crop_bailout, 16),
    VAR_REAL(post_benesi_crop_scaleX, 1),
    VAR_REAL(post_benesi_crop_scaleY, 1),
    VAR_REAL(post_benesi_crop_ScaleZ, 1),
    VAR_REAL(post_benesi_crop_color, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double x = FPx * VAR(post_benesi_crop_scaleX);
    double y = FPy * VAR(post_benesi_crop_scaleY);
    double z = FPz * VAR(post_benesi_crop_ScaleZ);
    double x1 = x;
    double y1 = y;
    double z1 = z;
    for(int i = 0;
    i < VAR(post_benesi_crop_iterations);
    i++) {
        double r1 = y * y + z * z;
        double newx;
        if(x1 < 0.0 || x < sqrt(r1)) newx = x * x - r1;
        else newx = - x * x + r1;
        r1 = - 1.0 / sqrt(r1) * 2.0 * fabs(x);
        double newy = r1 * (y * y - z * z);
        double newz = r1 * 2.0 * y * z;
        x = newx;
        y = newy;
        z = newz;
        x += x1;
        y += y1;
        z += z1;
        double r = sqrt(x * x + y * y + z * z);
        if(r < VAR(post_benesi_crop_bailout)) {
            FPx = VVAR * FPx;
            FPy = VVAR * FPy;
            FPz = VVAR * FPz;
            TC = sin(r) * VAR(post_benesi_crop_color);
        } else {
            FPx = FPy = FPz = 0;
        }
    }
    return TRUE;
}
