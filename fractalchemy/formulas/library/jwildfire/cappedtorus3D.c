/*
    Fractalchemy formula library — translated from the JWildfire variation (by hand)
        CappedTorus3DFunc.java
    (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors, GNU Lesser General Public License v2.1 or
    later — https://github.com/thargor6/JWildfire; the distance function after Inigo Quilez,
    https://iquilezles.org/articles/distfunctions/). A solid primitive by rejection sampling: points are drawn in the
    unit cube until one lies inside the signed-distance shape (50 tries; a point that never lands inside adds
    nothing — JWildfire would hide it). Author of the original: Jesus Sosa.
    The formula compiler (fractalchemy/formulas/lang) runs this for both the numpy and GLSL engines.
*/

typedef struct {
    double cappedtorus3D_dx;
    double cappedtorus3D_dy;
    double cappedtorus3D_R1;
    double cappedtorus3D_R2;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("cappedtorus3D");

APO_VARIABLES(
    VAR_REAL(cappedtorus3D_dx, 0.866025),
    VAR_REAL(cappedtorus3D_dy, -0.5),
    VAR_REAL(cappedtorus3D_R1, 0.25),
    VAR_REAL(cappedtorus3D_R2, 0.15)
);


double cappedtorus3D_sd(double px, double py, double pz, double scx, double scy, double ra, double rb)
{
    px = fabs(px);
    double k = (scy * px > scx * py) ? (px * scx + py * scy) : sqrt(px * px + py * py);
    return sqrt(px * px + py * py + pz * pz + ra * ra - 2.0 * ra * k) - rb;
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
        if (cappedtorus3D_sd(x, y, z, VAR(cappedtorus3D_dx), VAR(cappedtorus3D_dy), VAR(cappedtorus3D_R1), VAR(cappedtorus3D_R2)) < 0.0) inside = 1;
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
