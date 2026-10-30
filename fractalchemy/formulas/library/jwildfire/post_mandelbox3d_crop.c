/*
    Fractalchemy formula library — translated from the JWildfire variation (by hand)
        PostMandelbox3dCropFunc.java
    (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors, GNU Lesser General Public License v2.1 or
    later — https://github.com/thargor6/JWildfire). A 3D fractal used as a crop: the point is kept (and its colour set) when its orbit stays bounded, else set to
    the origin (JWildfire hides it; the engines cannot).
    The formula compiler (fractalchemy/formulas/lang) runs this for both the numpy and GLSL engines.
*/

typedef struct {
    double post_mandelbox3d_crop_scale;
    double post_mandelbox3d_crop_radius;
    double post_mandelbox3d_crop_f;
    int post_mandelbox3d_crop_iterations;
    double post_mandelbox3d_crop_bailout;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("post_mandelbox3d_crop");

APO_VARIABLES(
    VAR_REAL(post_mandelbox3d_crop_scale, 2.0),
    VAR_REAL(post_mandelbox3d_crop_radius, 0.5),
    VAR_REAL(post_mandelbox3d_crop_f, 1.0),
    VAR_INTEGER(post_mandelbox3d_crop_iterations, 12),
    VAR_REAL(post_mandelbox3d_crop_bailout, 16.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double x = FPx * 6.0, y = FPy * 6.0, z = FPz * 6.0;
    double x1 = x, y1 = y, z1 = z;
    double r = VAR(post_mandelbox3d_crop_radius);
    double f = VAR(post_mandelbox3d_crop_f);
    int inside = 0;
    for (int i = 0; i < VAR(post_mandelbox3d_crop_iterations); i++) {
        if (x > 1.0) x = 2.0 - x; else if (x < -1.0) x = -2.0 - x;
        if (y > 1.0) y = 2.0 - y; else if (y < -1.0) y = -2.0 - y;
        if (z > 1.0) z = 2.0 - z; else if (z < -1.0) z = -2.0 - z;
        x *= f;
        y *= f;
        z *= f;
        double mag = sqrt(x * x + y * y + z * z);
        if (mag < r) {
            x = x / (r * r);
            y = y / (r * r);
            z = z / (r * r);
        } else {
            x = x / (mag * mag);
            y = y / (mag * mag);
            z = z / (mag * mag);
        }
        x = x * VAR(post_mandelbox3d_crop_scale) + x1;
        y = y * VAR(post_mandelbox3d_crop_scale) + y1;
        z = z * VAR(post_mandelbox3d_crop_scale) + z1;
        inside = (mag < VAR(post_mandelbox3d_crop_bailout)) ? 1 : 0;
    }
    if (inside == 1) {
        FPx = VVAR * FPx;
        FPy = VVAR * FPy;
        FPz = VVAR * FPz;
    } else {
        FPx = FPy = FPz = 0;
    }
    return TRUE;
}
