/*
    Fractalchemy formula library — translated from the JWildfire variation
        PostBulbTorusCropFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double post_bulbtorus_crop_power1;
    double post_bulbtorus_crop_power2;
    int post_bulbtorus_crop_iterations;
    double post_bulbtorus_crop_bailout;
    double post_bulbtorus_crop_scaleX;
    double post_bulbtorus_crop_scaleY;
    double post_bulbtorus_crop_ScaleZ;
    double post_bulbtorus_crop_color;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("post_bulbtorus_crop");

APO_VARIABLES(
    VAR_REAL(post_bulbtorus_crop_power1, 9),
    VAR_REAL(post_bulbtorus_crop_power2, 9),
    VAR_INTEGER(post_bulbtorus_crop_iterations, 12),
    VAR_REAL(post_bulbtorus_crop_bailout, 16),
    VAR_REAL(post_bulbtorus_crop_scaleX, 1),
    VAR_REAL(post_bulbtorus_crop_scaleY, 1),
    VAR_REAL(post_bulbtorus_crop_ScaleZ, 1),
    VAR_REAL(post_bulbtorus_crop_color, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double x = FPx * VAR(post_bulbtorus_crop_scaleX);
    double y = FPy * VAR(post_bulbtorus_crop_scaleY);
    double z = FPz * VAR(post_bulbtorus_crop_ScaleZ);
    double x1 = x;
    double y1 = y;
    double z1 = z;
    double r = sqrt(x * x + y * y + z * z);
    for(int i = 0;
    i < VAR(post_bulbtorus_crop_iterations);
    i++) {
        double rh = sqrt(x * x + y * y);
        double phi = atan2(y, x);
        double phipow = phi * VAR(post_bulbtorus_crop_power1);
        double theta = atan2(rh, z);
        double px = x - cos(phi) * 1.5;
        double py = y - sin(phi) * 1.5;
        double rhrad = sqrt(px * px + py * py + z * z);
        double rh1 = pow(rhrad, VAR(post_bulbtorus_crop_power2));
        double rh2 = pow(rhrad, VAR(post_bulbtorus_crop_power1));
        double thetapow = theta * VAR(post_bulbtorus_crop_power2);
        double sintheta = sin(thetapow) * rh2;
        x = sintheta * cos(phipow);
        y = sintheta * sin(phipow);
        z = cos(thetapow) * rh1;
        x += x1;
        y += y1;
        z += z1;
        r = sqrt(x * x + y * y + z * z);
        if(r < VAR(post_bulbtorus_crop_bailout)) {
            FPx = VVAR * FPx;
            FPy = VVAR * FPy;
            FPz = VVAR * FPz;
            TC = sin(r) * VAR(post_bulbtorus_crop_color);
        } else {
            FPx = FPy = FPz = 0;
        }
    }
    return TRUE;
}
