/*
    Fractalchemy formula library — translated from the JWildfire variation (by hand)
        RoundBox3DFunc.java
    (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors, GNU Lesser General Public License v2.1 or
    later — https://github.com/thargor6/JWildfire; the distance function after Inigo Quilez,
    https://iquilezles.org/articles/distfunctions/). A solid primitive by rejection sampling: points are drawn in the
    unit cube until one lies inside the signed-distance shape (50 tries; a point that never lands inside adds
    nothing — JWildfire would hide it). Author of the original: Jesus Sosa.
    The formula compiler (fractalchemy/formulas/lang) runs this for both the numpy and GLSL engines.
*/

typedef struct {
    double rbox3D_dx;
    double rbox3D_dy;
    double rbox3D_dz;
    double rbox3D_r;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("rbox3D");

APO_VARIABLES(
    VAR_REAL(rbox3D_dx, 0.5),
    VAR_REAL(rbox3D_dy, 0.5),
    VAR_REAL(rbox3D_dz, 0.5),
    VAR_REAL(rbox3D_r, 0.05)
);


double rbox3D_sd(double px, double py, double pz, double bx, double by, double bz, double r)
{
    double qx = fabs(px) - bx, qy = fabs(py) - by, qz = fabs(pz) - bz;
    double mx = fmax(qx, 0.0), my = fmax(qy, 0.0), mz = fmax(qz, 0.0);
    return sqrt(mx * mx + my * my + mz * mz) + fmin(fmax(qx, fmax(qy, qz)), 0.0) - r;
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
        if (rbox3D_sd(x, y, z, VAR(rbox3D_dx), VAR(rbox3D_dy), VAR(rbox3D_dz), VAR(rbox3D_r)) < 0.0) inside = 1;
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
