/*
    Fractalchemy formula library — translated from the JWildfire variation (by hand)
        Ellipsoid3DFunc.java
    (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors, GNU Lesser General Public License v2.1 or
    later — https://github.com/thargor6/JWildfire; the distance function after Inigo Quilez,
    https://iquilezles.org/articles/distfunctions/). A solid primitive by rejection sampling: points are drawn in the
    unit cube until one lies inside the signed-distance shape (50 tries; a point that never lands inside adds
    nothing — JWildfire would hide it). Author of the original: Jesus Sosa.
    The formula compiler (fractalchemy/formulas/lang) runs this for both the numpy and GLSL engines.
*/

typedef struct {
    double ellipsoid3D_dx;
    double ellipsoid3D_dy;
    double ellipsoid3D_dz;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("ellipsoid3D");

APO_VARIABLES(
    VAR_REAL(ellipsoid3D_dx, 0.5),
    VAR_REAL(ellipsoid3D_dy, 0.5),
    VAR_REAL(ellipsoid3D_dz, 0.5)
);


double ellipsoid3D_sd(double px, double py, double pz, double rx, double ry, double rz)
{
    double ax = px / rx, ay = py / ry, az = pz / rz;
    double bx = px / (rx * rx), by = py / (ry * ry), bz = pz / (rz * rz);
    double k0 = sqrt(ax * ax + ay * ay + az * az);
    double k1 = sqrt(bx * bx + by * by + bz * bz);
    return k0 * (k0 - 1.0) / k1;
}

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double x = 0.0, y = 0.0, z = 0.0;
    int inside = 0;
    for (int i = 0; i < 50 && inside == 0; i++) {
        x = random01() - 0.5;
        y = random01() - 0.5;
        z = random01() - 0.5;
        if (ellipsoid3D_sd(x, y, z, VAR(ellipsoid3D_dx), VAR(ellipsoid3D_dy), VAR(ellipsoid3D_dz)) < 0.0) inside = 1;
    }
    if (inside == 0) {
        /* JWildfire hides the point (its position is left alone); the engines cannot hide, so nothing is added:
           the point stays where the other variations put it (the density threshold takes care of the rest) */
        return TRUE;
    }
    FPx += VVAR * x;
    FPy += VVAR * y;
    FPz += VVAR * z;
    return TRUE;
}
