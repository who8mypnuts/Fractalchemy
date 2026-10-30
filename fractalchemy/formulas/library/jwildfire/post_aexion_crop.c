/*
    Fractalchemy formula library — translated from the JWildfire variation (by hand)
        PostAexion3dCropFunc.java
    (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors, GNU Lesser General Public License v2.1 or
    later — https://github.com/thargor6/JWildfire). A 3D fractal used as a crop: the point is kept (and its colour set) when its orbit stays bounded, else set to
    the origin (JWildfire hides it; the engines cannot).
    The formula compiler (fractalchemy/formulas/lang) runs this for both the numpy and GLSL engines.
*/

typedef struct {
    int post_aexion_crop_Iters;
    double post_aexion_crop_cadd;
    double post_aexion_crop_bailout;
    double post_aexion_crop_scaleX;
    double post_aexion_crop_scaleY;
    double post_aexion_crop_ScaleZ;
    double post_aexion_crop_color;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("post_aexion_crop");

APO_VARIABLES(
    VAR_INTEGER(post_aexion_crop_Iters, 100),
    VAR_REAL(post_aexion_crop_cadd, -0.8),
    VAR_REAL(post_aexion_crop_bailout, 10.0),
    VAR_REAL(post_aexion_crop_scaleX, 1.0),
    VAR_REAL(post_aexion_crop_scaleY, 1.0),
    VAR_REAL(post_aexion_crop_ScaleZ, 1.0),
    VAR_REAL(post_aexion_crop_color, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double cadd = VAR(post_aexion_crop_cadd);
    double zx = FPx, zy = FPy, zz = FPz, zw = 1.0;
    double cx = fabs(FPx + FPy + FPz) + cadd;
    double cy = fabs(-FPx - FPy + FPz) + cadd;
    double cz = fabs(-FPx + FPy - FPz) + cadd;
    double cw = fabs(FPx - FPy - FPz) + cadd;
    double p0x = cx, p0y = cy, p0z = cz, p0w = cw;
    double ax = cx * VAR(post_aexion_crop_scaleX), ay = cy * VAR(post_aexion_crop_scaleY), az = cz * VAR(post_aexion_crop_ScaleZ);
    double tx = fabs(zx + zy + zz) + cadd;
    double ty = fabs(-zx - zy + zz) + cadd;
    double tz = fabs(-zx + zy - zz) + cadd;
    double tw = fabs(zx - zy - zz) + cadd;
    zx = tx * p0x;
    zy = ty * p0y;
    zz = tz * p0z;
    zw = tw * p0w;
    int inside = 0;
    double r = 0.0;
    for (int i = 0; i < VAR(post_aexion_crop_Iters); i++) {
        tx = zx * zx - zy * zy + 2.0 * zw * zz + ax;
        ty = zy * zy - zx * zx + 2.0 * zw * zz + ay;
        tz = zz * zz - zw * zw + 2.0 * zx * zy + az;
        zx = tx + p0x;
        zy = ty + p0y;
        zz = tz + p0z;
        zw = tw + p0w;
        r = sqrt(zx * zx + zy * zy + zz * zz + zw * zw);
        inside = (r < VAR(post_aexion_crop_bailout)) ? 1 : 0;
    }
    if (inside == 1) {
        FPx = VVAR * FPx;
        FPy = VVAR * FPy;
        FPz = VVAR * FPz;
        TC = sin(r) * VAR(post_aexion_crop_color);
    } else {
        FPx = FPy = FPz = 0;
    }
    return TRUE;
}
