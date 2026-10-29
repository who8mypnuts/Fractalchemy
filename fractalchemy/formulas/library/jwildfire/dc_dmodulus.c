/*
    Fractalchemy formula library — translated from the JWildfire variation
        DCDModulusFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

// keeps a private orbit between points (JWildfire fields updated per point): the statics below
typedef struct {
    double dc_dmodulus_x;
    double dc_dmodulus_y;
    double dc_dmodulus_shiftx;
    double dc_dmodulus_shifty;
    double dc_dmodulus_color1;
    double dc_dmodulus_color2;
    double dc_dmodulus_speed1;
    double dc_dmodulus_speed2;
    double dc_dmodulus_angle;
    int dc_dmodulus_square;
    double dc_dmodulus_coscos;
    double dc_dmodulus_sincos;
    double dc_dmodulus_sinsin;
    double dc_dmodulus_rangle;
    double dc_dmodulus__xr;
    double dc_dmodulus__yr;
    double dc_dmodulus_c11;
    double dc_dmodulus_c12;
    double dc_dmodulus_c21;
    double dc_dmodulus_c22;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("dc_dmodulus");

APO_VARIABLES(
    VAR_REAL(dc_dmodulus_x, 2),
    VAR_REAL(dc_dmodulus_y, 2),
    VAR_REAL(dc_dmodulus_angle, 45),
    VAR_REAL(dc_dmodulus_shiftx, 0),
    VAR_REAL(dc_dmodulus_shifty, 0),
    VAR_REAL(dc_dmodulus_color1, 0),
    VAR_REAL(dc_dmodulus_speed1, 0),
    VAR_REAL(dc_dmodulus_color2, 1),
    VAR_REAL(dc_dmodulus_speed2, 0),
    VAR_INTEGER(dc_dmodulus_square, 1)
);

static double oldColor = 0;
static double newColor = 0;

int PluginVarPrepare(Variation* vp)
{
    VAR(dc_dmodulus__xr) = 2.0 * VAR(dc_dmodulus_x);
    VAR(dc_dmodulus__yr) = 2.0 * VAR(dc_dmodulus_y);
    VAR(dc_dmodulus_c11) = (1 + VAR(dc_dmodulus_speed1)) / 2;
    VAR(dc_dmodulus_c12) = VAR(dc_dmodulus_color1) * (1 - VAR(dc_dmodulus_speed1)) / 2;
    VAR(dc_dmodulus_c21) = (1 + VAR(dc_dmodulus_speed2)) / 2;
    VAR(dc_dmodulus_c22) = VAR(dc_dmodulus_color2) * (1 - VAR(dc_dmodulus_speed2)) / 2;
    oldColor = 0.5;
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double xnew, ynew, xt, yt;
    double p2 = VAR(dc_dmodulus_coscos) / (VAR(dc_dmodulus_coscos) + VAR(dc_dmodulus_sinsin));
    double p1 = VAR(dc_dmodulus_sinsin) / (VAR(dc_dmodulus_coscos) + VAR(dc_dmodulus_sinsin));
    if(FTx > VAR(dc_dmodulus_x)) {
        xnew = (- VAR(dc_dmodulus_x) + fmod(FTx + VAR(dc_dmodulus_x), VAR(dc_dmodulus__xr)));
    } else if(FTx < - VAR(dc_dmodulus_x)) {
        xnew = (VAR(dc_dmodulus_x) - fmod(VAR(dc_dmodulus_x) - FTx, VAR(dc_dmodulus__xr)));
    } else {
        xnew = FTx;
    }
    if(FTy > VAR(dc_dmodulus_y)) {
        ynew = (- VAR(dc_dmodulus_y) + fmod(FTy + VAR(dc_dmodulus_y), VAR(dc_dmodulus__yr)));
    } else if(FTy < - VAR(dc_dmodulus_y)) {
        ynew = (VAR(dc_dmodulus_y) - fmod(VAR(dc_dmodulus_y) - FTy, VAR(dc_dmodulus__yr)));
    } else {
        ynew = FTy;
    }
    double p = random01();
    if(VAR(dc_dmodulus_angle) <= 45.0) {
        if(p < p2) {
            xt = xnew * VAR(dc_dmodulus_coscos) + ynew * VAR(dc_dmodulus_sincos) + VAR(dc_dmodulus_x);
            yt = - xnew * VAR(dc_dmodulus_sincos) + ynew * VAR(dc_dmodulus_coscos) - VAR(dc_dmodulus_y);
            newColor = oldColor * VAR(dc_dmodulus_c11) + VAR(dc_dmodulus_c12);
        } else {
            xt = xnew * VAR(dc_dmodulus_sincos) + ynew * VAR(dc_dmodulus_sinsin);
            yt = - xnew * VAR(dc_dmodulus_sinsin) + ynew * VAR(dc_dmodulus_sincos);
            newColor = oldColor * VAR(dc_dmodulus_c21) + VAR(dc_dmodulus_c22);
        }
    } else {
        if(p < p1) {
            xt = xnew * VAR(dc_dmodulus_sincos) + ynew * VAR(dc_dmodulus_sinsin);
            yt = - xnew * VAR(dc_dmodulus_sinsin) + ynew * VAR(dc_dmodulus_sincos);
            newColor = oldColor * VAR(dc_dmodulus_c21) + VAR(dc_dmodulus_c22);
        } else {
            xt = xnew * VAR(dc_dmodulus_coscos) + ynew * VAR(dc_dmodulus_sincos) + VAR(dc_dmodulus_x);
            yt = - xnew * VAR(dc_dmodulus_sincos) + ynew * VAR(dc_dmodulus_coscos) - VAR(dc_dmodulus_y);
            newColor = oldColor * VAR(dc_dmodulus_c11) + VAR(dc_dmodulus_c12);
        }
    }
    xt += VAR(dc_dmodulus_shiftx);
    yt += VAR(dc_dmodulus_shifty);
    if(VAR(dc_dmodulus_square) == 0) {
        FPx += VVAR * xt;
        FPy += VVAR * yt;
    } else {
        if(xt > VAR(dc_dmodulus_x)) {
            FPx += VVAR * (- VAR(dc_dmodulus_x) + fmod(xt + VAR(dc_dmodulus_x), VAR(dc_dmodulus__xr)));
        } else if(xt < - VAR(dc_dmodulus_x)) {
            FPx += VVAR * (VAR(dc_dmodulus_x) - fmod(VAR(dc_dmodulus_x) - xt, VAR(dc_dmodulus__xr)));
        } else {
            FPx += VVAR * xt;
        }
        if(yt > VAR(dc_dmodulus_y)) {
            FPy += VVAR * (- VAR(dc_dmodulus_y) + fmod(yt + VAR(dc_dmodulus_y), VAR(dc_dmodulus__yr)));
        } else if(yt < - VAR(dc_dmodulus_y)) {
            FPy += VVAR * (VAR(dc_dmodulus_y) - fmod(VAR(dc_dmodulus_y) - yt, VAR(dc_dmodulus__yr)));
        } else {
            FPy += VVAR * yt;
        }
    }
    
    TC = fmod(newColor, 1);
    oldColor = newColor;
    return TRUE;
}
