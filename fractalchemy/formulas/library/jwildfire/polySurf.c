/*
    Fractalchemy formula library — translated from the JWildfire variation
        PolySurfFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double polySurf_c;
    int polySurf_mirrorX;
    int polySurf_mirrorY;
    int polySurf_mirrorZ;
    int polySurf_julia;
    double polySurf_juliaX;
    double polySurf_juliaY;
    double polySurf_juliaZ;
    int polySurf_enableFold;
    double polySurf_foldX;
    double polySurf_foldY;
    double polySurf_rotX;
    double polySurf_rotY;
    double polySurf_rotZ;
    int polySurf_enableOffset;
    double polySurf_offsetX;
    double polySurf_offsetY;
    double polySurf_offsetZ;
    int polySurf_enableInvert;
    double polySurf_invertRadius;
    int polySurf_colorMode;
    double polySurf_colorSpeed;
    double polySurf_c2z;
    double polySurf_c2;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("polySurf");

APO_VARIABLES(
    VAR_REAL(polySurf_c, 0.3),
    VAR_INTEGER(polySurf_mirrorX, 1),
    VAR_INTEGER(polySurf_mirrorY, 1),
    VAR_INTEGER(polySurf_mirrorZ, 0),
    VAR_INTEGER(polySurf_julia, 0),
    VAR_REAL(polySurf_juliaX, 0),
    VAR_REAL(polySurf_juliaY, 0),
    VAR_REAL(polySurf_juliaZ, 0),
    VAR_INTEGER(polySurf_enableFold, 0),
    VAR_REAL(polySurf_foldX, 1),
    VAR_REAL(polySurf_foldY, 1),
    VAR_REAL(polySurf_rotX, 0),
    VAR_REAL(polySurf_rotY, 0),
    VAR_REAL(polySurf_rotZ, 0),
    VAR_INTEGER(polySurf_enableOffset, 1),
    VAR_REAL(polySurf_offsetX, 1),
    VAR_REAL(polySurf_offsetY, 1),
    VAR_REAL(polySurf_offsetZ, 0),
    VAR_INTEGER(polySurf_enableInvert, 0),
    VAR_REAL(polySurf_invertRadius, 1),
    VAR_INTEGER(polySurf_colorMode, 0),
    VAR_REAL(polySurf_colorSpeed, 1)
);

double radians(double d) { return d * M_PI / 180.0; }
double sqr(double pVal)
{
    return pVal * pVal;
}

int PluginVarPrepare(Variation* vp)
{
    VAR(polySurf_c2z) = 2 * VAR(polySurf_c);
    VAR(polySurf_c2) = sqr(VAR(polySurf_c));
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double sign_x = FTx >= 0 ? 1.0 : - 1.0;
    double sign_y = FTy >= 0 ? 1.0 : - 1.0;
    double x_calc = FTx;
    double y_calc = FTy;
    double z_calc = FTz;
    if(VAR(polySurf_julia) > 0) {
        x_calc += VAR(polySurf_juliaX);
        y_calc += VAR(polySurf_juliaY);
        z_calc += VAR(polySurf_juliaZ);
    }
    if(VAR(polySurf_enableFold) > 0) {
        x_calc = fabs(x_calc + VAR(polySurf_foldX)) - fabs(x_calc - VAR(polySurf_foldX)) - x_calc;
        y_calc = fabs(y_calc + VAR(polySurf_foldY)) - fabs(y_calc - VAR(polySurf_foldY)) - y_calc;
    }
    if(VAR(polySurf_enableOffset) > 0) {
        x_calc += VAR(polySurf_offsetX);
        y_calc += VAR(polySurf_offsetY);
        z_calc += VAR(polySurf_offsetZ);
    }
    double x_abs = fabs(x_calc);
    double y_abs = fabs(y_calc);
    double r2 = sqr(x_abs) + sqr(y_abs) + sqr(z_calc);
    double r = VVAR / (r2 * VAR(polySurf_c2) + VAR(polySurf_c2z) * z_calc + 1);
    double delta_x = r * x_abs;
    double delta_y = r * y_abs;
    double delta_z = r * (z_calc + VAR(polySurf_c) * r2);
    if(VAR(polySurf_rotX) != 0.0 || VAR(polySurf_rotY) != 0.0 || VAR(polySurf_rotZ) != 0.0) {
        double radX = radians(VAR(polySurf_rotX));
        double radY = radians(VAR(polySurf_rotY));
        double radZ = radians(VAR(polySurf_rotZ));
        double cosX = cos(radX), sinX = sin(radX);
        double cosY = cos(radY), sinY = sin(radY);
        double cosZ = cos(radZ), sinZ = sin(radZ);
        double temp_x, temp_y, temp_z;
        temp_y = delta_y * cosX - delta_z * sinX;
        temp_z = delta_y * sinX + delta_z * cosX;
        delta_y = temp_y;
        delta_z = temp_z;
        temp_x = delta_x * cosY + delta_z * sinY;
        temp_z = - delta_x * sinY + delta_z * cosY;
        delta_x = temp_x;
        delta_z = temp_z;
        temp_x = delta_x * cosZ - delta_y * sinZ;
        temp_y = delta_x * sinZ + delta_y * cosZ;
        delta_x = temp_x;
        delta_y = temp_y;
    }
    if(VAR(polySurf_enableInvert) > 0) {
        double r2_inv = sqr(delta_x) + sqr(delta_y) + sqr(delta_z);
        if(r2_inv > 1.0E-9) {
            double factor = sqr(VAR(polySurf_invertRadius)) / r2_inv;
            delta_x *= factor;
            delta_y *= factor;
            delta_z *= factor;
        }
    }
    FPx += (VAR(polySurf_mirrorX) > 0 && random01() < 0.5 ? - 1.0 : 1.0) * sign_x * delta_x;
    FPy += (VAR(polySurf_mirrorY) > 0 && random01() < 0.5 ? - 1.0 : 1.0) * sign_y * delta_y;
    FPz += (VAR(polySurf_mirrorZ) > 0 && random01() < 0.5 ? - 1.0 : 1.0) * delta_z;
    if(VAR(polySurf_colorMode) > 0) {
        double calculatedColor = 0.0;
        switch(VAR(polySurf_colorMode)) {
            case 1 : calculatedColor = sqrt(sqr(delta_x) + sqr(delta_y) + sqr(delta_z));
            break;
            case 2 : calculatedColor = (atan2(delta_y, delta_x) / (2.0 * M_PI)) + 0.5;
            break;
            case 3 : calculatedColor = delta_z;
            break;
        }
        calculatedColor *= VAR(polySurf_colorSpeed);
        calculatedColor = fmod(fmod(calculatedColor, 1.0) + 1.0, 1.0);
        TC += (calculatedColor - TC) * VVAR;
    }
    return TRUE;
}
