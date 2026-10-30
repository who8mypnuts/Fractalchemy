/*
    Fractalchemy formula library — translated from the JWildfire variation (by hand)
        PostMandelbulb3dCropFunc.java
    (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors, GNU Lesser General Public License v2.1 or
    later — https://github.com/thargor6/JWildfire). A 3D fractal used as a crop: the point is kept (and its colour set) when its orbit stays bounded, else set to
    the origin (JWildfire hides it; the engines cannot).
    The formula compiler (fractalchemy/formulas/lang) runs this for both the numpy and GLSL engines.
*/

typedef struct {
    double post_mandelbulb3d_crop_power;
    double post_mandelbulb3d_crop_xz;
    int post_mandelbulb3d_crop_iterations;
    double post_mandelbulb3d_crop_bailout;
    int post_mandelbulb3d_crop_filled;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("post_mandelbulb3d_crop");

APO_VARIABLES(
    VAR_REAL(post_mandelbulb3d_crop_power, 9.0),
    VAR_REAL(post_mandelbulb3d_crop_xz, 0.0),
    VAR_INTEGER(post_mandelbulb3d_crop_iterations, 12),
    VAR_REAL(post_mandelbulb3d_crop_bailout, 2.0),
    VAR_INTEGER(post_mandelbulb3d_crop_filled, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    if (VAR(post_mandelbulb3d_crop_filled) == 1) {
        double fillAmount = (VVAR + 1.0) * 2.0;
        FPx = random01() * fillAmount - fillAmount / 2.0;
        FPy = random01() * fillAmount - fillAmount / 2.0;
        FPz = random01() * fillAmount - fillAmount / 2.0;
    }
    double x = FPx, y = FPy, z = FPz;
    double power = VAR(post_mandelbulb3d_crop_power);
    int inside = 0;
    for (int i = 0; i < VAR(post_mandelbulb3d_crop_iterations); i++) {
        double sq_r = sqrt(x * x + y * y + z * z);
        double sq_xz = sqrt(x * x + z * z);
        double r = pow(sq_r, power);
        double theta = atan2(sq_xz + VAR(post_mandelbulb3d_crop_xz), y) * power;
        double zangle = atan2(x, z) * power;
        double xf = sin(zangle) * sin(theta) * r + x;
        double yf = cos(theta) * r + y;
        double zf = sin(theta) * cos(zangle) * r + z;
        x = xf;
        y = yf;
        z = zf;
        TC = fmin(1.0, 8.0 / (double)(i + 1));
        inside = (sqrt(xf * xf + yf * yf + zf * zf) < VAR(post_mandelbulb3d_crop_bailout)) ? 1 : 0;
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
