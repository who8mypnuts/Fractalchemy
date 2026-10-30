/*
    Fractalchemy formula library — translated from the JWildfire variation (by hand)
        HexPrism3DFunc.java
    (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors, GNU Lesser General Public License v2.1 or
    later — https://github.com/thargor6/JWildfire; the distance function after Inigo Quilez,
    https://iquilezles.org/articles/distfunctions/). A solid primitive by rejection sampling: points are drawn in the
    unit cube until one lies inside the signed-distance shape (50 tries; a point that never lands inside adds
    nothing — JWildfire would hide it). Author of the original: Jesus Sosa.
    The formula compiler (fractalchemy/formulas/lang) runs this for both the numpy and GLSL engines.
*/

typedef struct {
    double hexprism3D_d;
    double hexprism3D_H;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("hexprism3D");

APO_VARIABLES(
    VAR_REAL(hexprism3D_d, 0.3),
    VAR_REAL(hexprism3D_H, 0.25)
);


double hexprism3D_sd(double px, double py, double pz, double hx, double hy)
{
    double kx = -0.8660254, ky = 0.5, kz = 0.57735;
    px = fabs(px);
    py = fabs(py);
    pz = fabs(pz);
    double dot = 2.0 * fmin(kx * px + ky * py, 0.0);
    px = px - kx * dot;
    py = py - ky * dot;
    double cx = fmin(fmax(px, -kz * hx), kz * hx);
    double ex = px - cx, ey = py - hx;
    double dx = sqrt(ex * ex + ey * ey) * sign(py - hx);
    double dy = pz - hy;
    double mx = fmax(dx, 0.0), my = fmax(dy, 0.0);
    return fmin(fmax(dx, dy), 0.0) + sqrt(mx * mx + my * my);
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
        if (hexprism3D_sd(x, y, z, VAR(hexprism3D_d), VAR(hexprism3D_H)) < 0.0) inside = 1;
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
