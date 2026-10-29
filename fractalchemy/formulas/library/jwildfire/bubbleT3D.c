/*
    Fractalchemy formula library — translated from the JWildfire variation
        BubbleT3DFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

// keeps a private orbit between points (JWildfire fields updated per point): the statics below
typedef struct {
    int bubbleT3D_number_of_stripes;
    double bubbleT3D_ratio_of_stripes;
    double bubbleT3D_angle_of_hole;
    double bubbleT3D_exponent_z;
    int bubbleT3D_symmetry_z;
    int bubbleT3D_modus_blur;
    double bubbleT3D_angHoleComp;
    double bubbleT3D_angStrip;
    double bubbleT3D_angStrip1;
    double bubbleT3D_angStrip2;
    int bubbleT3D_invStripes;
    int bubbleT3D_invHole;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("bubbleT3D");

APO_VARIABLES(
    VAR_INTEGER(bubbleT3D_number_of_stripes, 0),
    VAR_REAL(bubbleT3D_ratio_of_stripes, 1),
    VAR_REAL(bubbleT3D_angle_of_hole, 0),
    VAR_REAL(bubbleT3D_exponent_z, 1),
    VAR_INTEGER(bubbleT3D_symmetry_z, 0),
    VAR_INTEGER(bubbleT3D_modus_blur, 0)
);

#define TRUE (1)
#define FALSE (0)
static double s = 0;
static double c = 0;

int PluginVarPrepare(Variation* vp)
{
    if(VAR(bubbleT3D_number_of_stripes) < 0) {
        VAR(bubbleT3D_number_of_stripes) = abs(VAR(bubbleT3D_number_of_stripes));
        VAR(bubbleT3D_invStripes) = TRUE;
    } else {
        VAR(bubbleT3D_invStripes) = FALSE;
    }
    if(VAR(bubbleT3D_number_of_stripes) != 0) {
        VAR(bubbleT3D_angStrip) = M_PI / (double) VAR(bubbleT3D_number_of_stripes);
        VAR(bubbleT3D_angStrip2) = 2 * VAR(bubbleT3D_angStrip);
        s = sin(VAR(bubbleT3D_angStrip));
        c = cos(VAR(bubbleT3D_angStrip));
        if(VAR(bubbleT3D_ratio_of_stripes) < 0.01) VAR(bubbleT3D_ratio_of_stripes) = 0.01;
        if(VAR(bubbleT3D_ratio_of_stripes) > 1.99) VAR(bubbleT3D_ratio_of_stripes) = 1.99;
        VAR(bubbleT3D_angStrip1) = VAR(bubbleT3D_ratio_of_stripes) * VAR(bubbleT3D_angStrip);
    }
    if(VAR(bubbleT3D_symmetry_z) == TRUE) {
        if(VAR(bubbleT3D_angle_of_hole) < 0.0) VAR(bubbleT3D_angle_of_hole) = fabs(VAR(bubbleT3D_angle_of_hole));
        if(VAR(bubbleT3D_angle_of_hole) > 179.9) VAR(bubbleT3D_angle_of_hole) = 179.9;
    }
    if(VAR(bubbleT3D_angle_of_hole) < 0) {
        VAR(bubbleT3D_angle_of_hole) = fabs(VAR(bubbleT3D_angle_of_hole));
        VAR(bubbleT3D_invHole) = TRUE;
        VAR(bubbleT3D_angle_of_hole) = (VAR(bubbleT3D_angle_of_hole) / 360 * (2.0 * M_PI)) / 2;
    } else {
        VAR(bubbleT3D_invHole) = FALSE;
        VAR(bubbleT3D_angle_of_hole) = M_PI - (VAR(bubbleT3D_angle_of_hole) / 360 * (2.0 * M_PI)) / 2;
    }
    VAR(bubbleT3D_angHoleComp) = M_PI - VAR(bubbleT3D_angle_of_hole);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double x = FTx, y = FTy, z = FTz;
    double xTmp, yTmp, angTmp, angRot, fac;
    double rad = (sqr(x) + sqr(y)) / 4 + 1;
    double angXY, angZ;
    angXY = atan2(x, y);
    if(angXY < 0) angXY += (2.0 * M_PI);
    if(VAR(bubbleT3D_number_of_stripes) != 0) {
        while(angXY > VAR(bubbleT3D_angStrip2)) {
            angXY -= VAR(bubbleT3D_angStrip2);
        }
        if(VAR(bubbleT3D_invStripes) == FALSE) {
            if(angXY > VAR(bubbleT3D_angStrip1)) {
                if(VAR(bubbleT3D_modus_blur) == FALSE) {
                    x = 0.0;
                    y = 0.0;
                } else {
                    if(VAR(bubbleT3D_ratio_of_stripes) == 1) {
                        xTmp = c * x - s * y;
                        yTmp = s * x + c * y;
                        x = xTmp;
                        y = yTmp;
                    } else {
                        angRot = (angXY - VAR(bubbleT3D_angStrip1)) / (VAR(bubbleT3D_angStrip2) - VAR(bubbleT3D_angStrip1));
                        angRot = angXY - angRot * VAR(bubbleT3D_angStrip1);
                        s = sin(angRot);
                        c = cos(angRot);
                        xTmp = c * x - s * y;
                        yTmp = s * x + c * y;
                        x = xTmp;
                        y = yTmp;
                    }
                }
            }
        } else {
            if(angXY < VAR(bubbleT3D_angStrip1)) {
                if(VAR(bubbleT3D_modus_blur) == FALSE) {
                    x = 0.0;
                    y = 0.0;
                } else {
                    if(VAR(bubbleT3D_ratio_of_stripes) == 1) {
                        xTmp = c * x - s * y;
                        yTmp = s * x + c * y;
                        x = xTmp;
                        y = yTmp;
                    } else {
                        angRot = (angXY - VAR(bubbleT3D_angStrip1)) / (VAR(bubbleT3D_angStrip1));
                        angRot = angXY - angRot * (VAR(bubbleT3D_angStrip2) - VAR(bubbleT3D_angStrip1));
                        s = sin(angRot);
                        c = cos(angRot);
                        xTmp = c * x - s * y;
                        yTmp = s * x + c * y;
                        x = xTmp;
                        y = yTmp;
                    }
                }
            }
        }
    }
    x = x / rad;
    y = y / rad;
    if((x != 0) || (y != 0)) {
        z = 2 / pow(rad, VAR(bubbleT3D_exponent_z)) - 1;
        if(VAR(bubbleT3D_exponent_z) <= 2) angZ = M_PI - acos((z / (x * x + y * y + z * z)));
        else angZ = M_PI - atan2(sqr(x * x + y * y), z);
    } else {
        z = 0.0;
        angZ = 0.0;
    }
    if(VAR(bubbleT3D_symmetry_z) == FALSE) {
        if(VAR(bubbleT3D_invHole) == FALSE) {
            if(angZ > VAR(bubbleT3D_angle_of_hole)) {
                if((VAR(bubbleT3D_modus_blur) == FALSE) || (VAR(bubbleT3D_exponent_z) != 1.0)) {
                    x = 0.0;
                    y = 0.0;
                    z = 0.0;
                } else {
                    angTmp = (M_PI - angZ) / VAR(bubbleT3D_angHoleComp) * VAR(bubbleT3D_angle_of_hole) - M_PI_2;
                    angZ -= M_PI_2;
                    fac = cos(angTmp) / cos(angZ);
                    x = x * fac;
                    y = y * fac;
                    z = z * (sin(angTmp) / sin(angZ));
                }
            }
        } else {
            if(angZ < VAR(bubbleT3D_angle_of_hole)) {
                if((VAR(bubbleT3D_modus_blur) == FALSE) || (VAR(bubbleT3D_exponent_z) != 1.0)) {
                    x = 0.0;
                    y = 0.0;
                    z = 0.0;
                } else {
                    angTmp = M_PI - angZ / VAR(bubbleT3D_angHoleComp) * VAR(bubbleT3D_angle_of_hole) - M_PI_2;
                    angZ -= M_PI_2;
                    fac = cos(angTmp) / cos(angZ);
                    x = x * fac;
                    y = y * fac;
                    z = z * (sin(angTmp) / sin(angZ));
                }
            }
        }
    } else {
        if((angZ > VAR(bubbleT3D_angle_of_hole)) || (angZ < (M_PI - VAR(bubbleT3D_angle_of_hole)))) {
            if((VAR(bubbleT3D_modus_blur) == FALSE) || (VAR(bubbleT3D_exponent_z) != 1.0)) {
                x = 0.0;
                y = 0.0;
                z = 0.0;
            } else {
                if(angZ > VAR(bubbleT3D_angle_of_hole)) {
                    angTmp = (M_PI - angZ) / VAR(bubbleT3D_angHoleComp) * (M_PI - 2 * VAR(bubbleT3D_angHoleComp)) + VAR(bubbleT3D_angHoleComp) - M_PI_2;
                } else {
                    angTmp = M_PI_2 - (angZ / VAR(bubbleT3D_angHoleComp) * (M_PI - 2 * VAR(bubbleT3D_angHoleComp)) + VAR(bubbleT3D_angHoleComp));
                }
                angZ -= M_PI_2;
                fac = cos(angTmp) / cos(angZ);
                x = x * fac;
                y = y * fac;
                z = z * (sin(angTmp) / sin(angZ));
            }
        }
    }
    FPx += VVAR * x;
    FPy += VVAR * y;
    FPz += VVAR * z;
    return TRUE;
}
