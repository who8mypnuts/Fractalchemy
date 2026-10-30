/*
    Fractalchemy formula library — translated from the JWildfire variation (by hand)
        Cone3DFunc.java
    (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors, GNU Lesser General Public License v2.1 or
    later — https://github.com/thargor6/JWildfire; the distance function after Inigo Quilez,
    https://iquilezles.org/articles/distfunctions/). A solid primitive by rejection sampling: points are drawn in the
    unit cube until one lies inside the signed-distance shape (50 tries; a point that never lands inside adds
    nothing — JWildfire would hide it). Author of the original: Jesus Sosa.
    The formula compiler (fractalchemy/formulas/lang) runs this for both the numpy and GLSL engines.
*/

typedef struct {
    double cone3D_w;
    double cone3D_h;
    double cone3D_Ty;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("cone3D");

APO_VARIABLES(
    VAR_REAL(cone3D_w, 0.25),
    VAR_REAL(cone3D_h, 0.25),
    VAR_REAL(cone3D_Ty, 0.1)
);


double cone3D_sd(double px, double py, double pz, double cx, double cy, double h)
{
    double qx = cx * (h / cy), qy = -cy * (h / cy);
    double wx = sqrt(px * px + pz * pz), wy = py;
    double t = fmin(fmax((wx * qx + wy * qy) / (qx * qx + qy * qy), 0.0), 1.0);
    double ax = wx - qx * t, ay = wy - qy * t;
    double u = fmin(fmax(wx / qx, 0.0), 1.0);
    double bx = wx - qx * u, by = wy - qy;
    double k = sign(qy);
    double d = fmin(ax * ax + ay * ay, bx * bx + by * by);
    double s = fmax(k * (wx * qy - wy * qx), k * (wy - qy));
    return sqrt(d) * sign(s);
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
        if (cone3D_sd(x, y, z, VAR(cone3D_w), VAR(cone3D_h), VAR(cone3D_Ty)) < 0.0) inside = 1;
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
