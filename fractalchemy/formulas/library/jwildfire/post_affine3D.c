/*
    Fractalchemy formula library — translated from the JWildfire variation (by hand)
        PostAffine3DFunc.java (AbstractAffine3DFunc.java)
    (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors, GNU Lesser General Public License v2.1 or
    later — https://github.com/thargor6/JWildfire). A full 3D affine map — translate, scale, rotate (degrees, about x then y then z) and shear — the natural
    transform of a 3D IFS. This one rewrites the result after the other variations.
    The formula compiler (fractalchemy/formulas/lang) runs this for both the numpy and GLSL engines.
*/

typedef struct {
    double post_affine3D_translateX;
    double post_affine3D_translateY;
    double post_affine3D_translateZ;
    double post_affine3D_scaleX;
    double post_affine3D_scaleY;
    double post_affine3D_scaleZ;
    double post_affine3D_rotateX;
    double post_affine3D_rotateY;
    double post_affine3D_rotateZ;
    double post_affine3D_shearXY;
    double post_affine3D_shearXZ;
    double post_affine3D_shearYX;
    double post_affine3D_shearYZ;
    double post_affine3D_shearZX;
    double post_affine3D_shearZY;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("post_affine3D");

APO_VARIABLES(
    VAR_REAL(post_affine3D_translateX, 0.0),
    VAR_REAL(post_affine3D_translateY, 0.0),
    VAR_REAL(post_affine3D_translateZ, 0.0),
    VAR_REAL(post_affine3D_scaleX, 1.0),
    VAR_REAL(post_affine3D_scaleY, 1.0),
    VAR_REAL(post_affine3D_scaleZ, 1.0),
    VAR_REAL(post_affine3D_rotateX, 0.0),
    VAR_REAL(post_affine3D_rotateY, 0.0),
    VAR_REAL(post_affine3D_rotateZ, 0.0),
    VAR_REAL(post_affine3D_shearXY, 0.0),
    VAR_REAL(post_affine3D_shearXZ, 0.0),
    VAR_REAL(post_affine3D_shearYX, 0.0),
    VAR_REAL(post_affine3D_shearYZ, 0.0),
    VAR_REAL(post_affine3D_shearZX, 0.0),
    VAR_REAL(post_affine3D_shearZY, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double xa = VAR(post_affine3D_rotateX) * M_PI / 180.0, ya = VAR(post_affine3D_rotateY) * M_PI / 180.0, za = VAR(post_affine3D_rotateZ) * M_PI / 180.0;
    double sx = sin(xa), cx = cos(xa), sy = sin(ya), cy = cos(ya), sz = sin(za), cz = cos(za);
    double inX = FPx, inY = FPy, inZ = FPz;
    double ex = VAR(post_affine3D_shearXY) * VAR(post_affine3D_scaleY) * inY + VAR(post_affine3D_shearXZ) * VAR(post_affine3D_scaleZ) * inZ + VAR(post_affine3D_scaleX) * inX;
    double ey = VAR(post_affine3D_shearYX) * VAR(post_affine3D_scaleX) * inX + VAR(post_affine3D_shearYZ) * VAR(post_affine3D_scaleZ) * inZ + VAR(post_affine3D_scaleY) * inY;
    double ez = VAR(post_affine3D_shearZX) * VAR(post_affine3D_scaleX) * inX + VAR(post_affine3D_shearZY) * VAR(post_affine3D_scaleY) * inY + VAR(post_affine3D_scaleZ) * inZ;
    double ax = VVAR * (cz * (cy * ex + sy * (sx * ey + cx * ez)) - sz * (cx * ey - sx * ez) + VAR(post_affine3D_translateX));
    double ay = VVAR * (sz * (cy * ex + sy * (sx * ey + cx * ez)) + cz * (cx * ey - sx * ez) + VAR(post_affine3D_translateY));
    double az = VVAR * (-sy * ex + cy * (sx * ey + cx * ez) + VAR(post_affine3D_translateZ));
    FPx = ax;
    FPy = ay;
    FPz = az;
    return TRUE;
}
