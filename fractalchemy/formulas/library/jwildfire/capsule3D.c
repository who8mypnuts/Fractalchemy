/*
    Fractalchemy formula library — translated from the JWildfire variation (by hand)
        Capsule3DFunc.java
    (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors, GNU Lesser General Public License v2.1 or
    later — https://github.com/thargor6/JWildfire; the distance function after Inigo Quilez,
    https://iquilezles.org/articles/distfunctions/). A solid primitive by rejection sampling: points are drawn in the
    unit cube until one lies inside the signed-distance shape (50 tries; a point that never lands inside adds
    nothing — JWildfire would hide it). Author of the original: Jesus Sosa.
    The formula compiler (fractalchemy/formulas/lang) runs this for both the numpy and GLSL engines.
*/

typedef struct {
    double capsule3D_dx;
    double capsule3D_dy;
    double capsule3D_dz;
    double capsule3D_tx;
    double capsule3D_ty;
    double capsule3D_tz;
    double capsule3D_R;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("capsule3D");

APO_VARIABLES(
    VAR_REAL(capsule3D_dx, 0.1),
    VAR_REAL(capsule3D_dy, 0.0),
    VAR_REAL(capsule3D_dz, 0.0),
    VAR_REAL(capsule3D_tx, 0.0),
    VAR_REAL(capsule3D_ty, 0.0),
    VAR_REAL(capsule3D_tz, 0.0),
    VAR_REAL(capsule3D_R, 0.05)
);


double capsule3D_sd(double px, double py, double pz, double ax, double ay, double az, double bx, double by, double bz, double r)
{
    double pax = px - ax, pay = py - ay, paz = pz - az;
    double bax = bx - ax, bay = by - ay, baz = bz - az;
    double bb = bax * bax + bay * bay + baz * baz;
    double h = bb > 0.0 ? fmin(fmax((pax * bax + pay * bay + paz * baz) / bb, 0.0), 1.0) : 0.0;
    double dx = pax - bax * h, dy = pay - bay * h, dz = paz - baz * h;
    return sqrt(dx * dx + dy * dy + dz * dz) - r;
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
        if (capsule3D_sd(x, y, z, VAR(capsule3D_dx), VAR(capsule3D_dy), VAR(capsule3D_dz), VAR(capsule3D_tx), VAR(capsule3D_ty), VAR(capsule3D_tz), VAR(capsule3D_R)) < 0.0) inside = 1;
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
