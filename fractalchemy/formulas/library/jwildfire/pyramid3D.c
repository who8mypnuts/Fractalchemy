/*
    Fractalchemy formula library — translated from the JWildfire variation (by hand)
        Pyramid3DFunc.java
    (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors, GNU Lesser General Public License v2.1 or
    later — https://github.com/thargor6/JWildfire; the distance function after Inigo Quilez,
    https://iquilezles.org/articles/distfunctions/). A solid primitive by rejection sampling: points are drawn in the
    unit cube until one lies inside the signed-distance shape (50 tries; a point that never lands inside adds
    nothing — JWildfire would hide it). Author of the original: Jesus Sosa.
    The formula compiler (fractalchemy/formulas/lang) runs this for both the numpy and GLSL engines.
*/

typedef struct {
    double pyramid3D_h;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("pyramid3D");

APO_VARIABLES(
    VAR_REAL(pyramid3D_h, 0.25)
);


double pyramid3D_sd(double px, double py, double pz, double h)
{
    double m2 = h * h + 0.25;
    px = fabs(px);
    pz = fabs(pz);
    if (pz > px) { px = pz; }          /* as the JWildfire original (a partial swap) */
    px = px - 0.5;
    pz = pz - 0.5;
    double qx = pz, qy = h * py - 0.5 * px, qz = h * px + 0.5 * py;
    double s = fmax(-qx, 0.0);
    double t = fmin(fmax((qy - 0.5 * pz) / (m2 + 0.25), 0.0), 1.0);
    double a = m2 * (qx + s) * (qx + s) + qy * qy;
    double b = m2 * (qx + 0.5 * t) * (qx + 0.5 * t) + (qy - m2 * t) * (qy - m2 * t);
    double d2 = fmin(qy, -qx * m2 - qy * 0.5) > 0.0 ? 0.0 : fmin(a, b);
    return sqrt((d2 + qz * qz) / m2) * sign(fmax(qz, -py));
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
        if (pyramid3D_sd(x, y, z, VAR(pyramid3D_h)) < 0.0) inside = 1;
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
