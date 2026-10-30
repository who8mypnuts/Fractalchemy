/*
    Fractalchemy formula library — translated from the JWildfire variation (by hand)
        Rhombus3DFunc.java
    (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors, GNU Lesser General Public License v2.1 or
    later — https://github.com/thargor6/JWildfire; the distance function after Inigo Quilez,
    https://iquilezles.org/articles/distfunctions/). A solid primitive by rejection sampling: points are drawn in the
    unit cube until one lies inside the signed-distance shape (50 tries; a point that never lands inside adds
    nothing — JWildfire would hide it). Author of the original: Jesus Sosa.
    The formula compiler (fractalchemy/formulas/lang) runs this for both the numpy and GLSL engines.
*/

typedef struct {
    double rhombus3D_la;
    double rhombus3D_lb;
    double rhombus3D_h;
    double rhombus3D_r;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("rhombus3D");

APO_VARIABLES(
    VAR_REAL(rhombus3D_la, 0.5),
    VAR_REAL(rhombus3D_lb, 0.5),
    VAR_REAL(rhombus3D_h, 0.5),
    VAR_REAL(rhombus3D_r, 0.05)
);


double rhombus3D_sd(double px, double py, double pz, double la, double lb, double h, double ra)
{
    px = fabs(px);
    py = fabs(py);
    pz = fabs(pz);
    double ndot = la * (la - 2.0 * px) - lb * (lb - 2.0 * pz);
    double f = fmin(fmax(ndot / (la * la + lb * lb), -1.0), 1.0);
    double ex = px - 0.5 * la * (1.0 - f), ez = pz - 0.5 * lb * (1.0 + f);
    double qx = sqrt(ex * ex + ez * ez) * sign(px * lb + pz * la - la * lb) - ra;
    double qy = py - h;
    double mx = fmax(qx, 0.0), my = fmax(qy, 0.0);
    return fmin(fmax(qx, qy), 0.0) + sqrt(mx * mx + my * my);
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
        if (rhombus3D_sd(x, y, z, VAR(rhombus3D_la), VAR(rhombus3D_lb), VAR(rhombus3D_h), VAR(rhombus3D_r)) < 0.0) inside = 1;
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
