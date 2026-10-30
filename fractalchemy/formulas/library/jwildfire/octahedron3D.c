/*
    Fractalchemy formula library — translated from the JWildfire variation (by hand)
        Octahedron3DFunc.java
    (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors, GNU Lesser General Public License v2.1 or
    later — https://github.com/thargor6/JWildfire; the distance function after Inigo Quilez,
    https://iquilezles.org/articles/distfunctions/). A solid primitive by rejection sampling: points are drawn in the
    unit cube until one lies inside the signed-distance shape (50 tries; a point that never lands inside adds
    nothing — JWildfire would hide it). Author of the original: Jesus Sosa.
    The formula compiler (fractalchemy/formulas/lang) runs this for both the numpy and GLSL engines.
*/

typedef struct {
    double octahedron3D_h;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("octahedron3D");

APO_VARIABLES(
    VAR_REAL(octahedron3D_h, 0.25)
);


double octahedron3D_sd(double px, double py, double pz, double s)
{
    px = fabs(px);
    py = fabs(py);
    pz = fabs(pz);
    double m = px + py + pz - s;
    double qx, qy, qz;
    if (3.0 * px < m) { qx = px; qy = py; qz = pz; }
    else if (3.0 * py < m) { qx = py; qy = pz; qz = px; }
    else if (3.0 * pz < m) { qx = pz; qy = px; qz = py; }
    else return m * 0.57735027;
    double k = fmin(fmax(0.5 * (qz - qy + s), 0.0), s);
    double ex = qx, ey = qy - s + k, ez = qz - k;
    return sqrt(ex * ex + ey * ey + ez * ez);
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
        if (octahedron3D_sd(x, y, z, VAR(octahedron3D_h)) < 0.0) inside = 1;
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
