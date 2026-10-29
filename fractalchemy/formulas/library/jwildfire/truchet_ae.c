/*
    Fractalchemy formula library — translated from the JWildfire variation
        TruchetAEFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

// keeps a private orbit between points (JWildfire fields updated per point): the statics below
typedef struct {
    int truchet_ae_seed;
    double truchet_ae_step;
    double truchet_ae_width;
    double truchet_ae_angle;
    int truchet_ae_layout;
    int truchet_ae_style;
    double truchet_ae_K01A;
    double truchet_ae_K02A;
    double truchet_ae_K01B;
    double truchet_ae_K02B;
    double truchet_ae_K11A;
    double truchet_ae_K12A;
    double truchet_ae_K11B;
    double truchet_ae_K12B;
    double truchet_ae_K21A;
    double truchet_ae_K22A;
    double truchet_ae_K21B;
    double truchet_ae_K22B;
    double truchet_ae_K31A;
    double truchet_ae_K32A;
    double truchet_ae_K31B;
    double truchet_ae_K32B;
    double truchet_ae_sinang;
    double truchet_ae_cosang;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("truchet_ae");

APO_VARIABLES(
    VAR_INTEGER(truchet_ae_seed, 0),
    VAR_REAL(truchet_ae_step, 0.5),
    VAR_REAL(truchet_ae_width, 0.25),
    VAR_REAL(truchet_ae_angle, 0),
    VAR_INTEGER(truchet_ae_layout, 0),
    VAR_INTEGER(truchet_ae_style, 0),
    VAR_REAL(truchet_ae_K01A, 0.5),
    VAR_REAL(truchet_ae_K02A, 0.5),
    VAR_REAL(truchet_ae_K01B, 0.5),
    VAR_REAL(truchet_ae_K02B, 0.5),
    VAR_REAL(truchet_ae_K11A, 0.5),
    VAR_REAL(truchet_ae_K12A, 0.5),
    VAR_REAL(truchet_ae_K11B, 0.5),
    VAR_REAL(truchet_ae_K12B, 0.5),
    VAR_REAL(truchet_ae_K21A, 0.5),
    VAR_REAL(truchet_ae_K22A, 0.5),
    VAR_REAL(truchet_ae_K21B, 0.5),
    VAR_REAL(truchet_ae_K22B, 0.5),
    VAR_REAL(truchet_ae_K31A, 0.5),
    VAR_REAL(truchet_ae_K32A, 0.5),
    VAR_REAL(truchet_ae_K31B, 0.5),
    VAR_REAL(truchet_ae_K32B, 0.5)
);

#define AM ((1.0 / 2147483647))
#define M_SQ3_2 (0.86602540378443864676372317075294)
static double x = 0;
static double y = 0;
static double z1 = 0;
static double z2 = 0;

double dn1(int x)
{
    int n = x;
    n = (n << 13) ^ n;
    return((n * (n * n * 15731 + 789221) + 1376312589) & 0x7fffffff) * AM;
}

double fmod2(double num, double den)
{
    double tmp = fmod(num, den);
    if((tmp < 0) && (den > 0)) tmp += den;
    return tmp;
}

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double u1 = 0, v1 = 0, z = 0.;
    int i = (int) floor(4 * random01());
    if(VAR(truchet_ae_layout) == 1) {
        switch(i) {
            case 0 : u1 = - x * 0.5 + 1.0;
            v1 = y * 0.5 + 1.0;
            z1 = fmod2(VAR(truchet_ae_K01A) * z1 + VAR(truchet_ae_K02A), 1.0);
            z2 = fmod2(VAR(truchet_ae_K01B) * z2 + VAR(truchet_ae_K02B), 1.0);
            break;
            case 1 : u1 = x * 0.5 - 1.0;
            v1 = y * 0.5 + 1.0;
            z1 = fmod2(VAR(truchet_ae_K11A) * z1 + VAR(truchet_ae_K12A), 1.0);
            z2 = fmod2(VAR(truchet_ae_K11B) * z2 + VAR(truchet_ae_K12B), 1.0);
            break;
            case 2 : u1 = - x * 0.5 + 1.0;
            v1 = - y * 0.5 - 1.0;
            z1 = fmod2(VAR(truchet_ae_K21A) * z1 + VAR(truchet_ae_K22A), 1.0);
            z2 = fmod2(VAR(truchet_ae_K21B) * z2 + VAR(truchet_ae_K22B), 0.5);
            break;
            case 3 : u1 = x * 0.5 - 1.0;
            v1 = - y * 0.5 - 1.0;
            z1 = fmod2(VAR(truchet_ae_K31A) * z1 + VAR(truchet_ae_K32A), 1.0);
            z2 = fmod2(VAR(truchet_ae_K31B) * z2 + VAR(truchet_ae_K32B), 1.0);
            break;
        }
    } else if(VAR(truchet_ae_layout) == 2) {
        switch(i) {
            case 0 : u1 = x * 0.5 + 1.0;
            v1 = y * 0.5 + 1.0;
            z1 = fmod2(VAR(truchet_ae_K01A) * z1 + VAR(truchet_ae_K02A), 1.0);
            z2 = fmod2(VAR(truchet_ae_K01B) * z2 + VAR(truchet_ae_K02B), 1.0);
            break;
            case 1 : u1 = x * 0.5 - 1.0;
            v1 = y * 0.5 - 1.0;
            z1 = fmod2(VAR(truchet_ae_K11A) * z1 + VAR(truchet_ae_K12A), 1.0);
            z2 = fmod2(VAR(truchet_ae_K11B) * z2 + VAR(truchet_ae_K12B), 1.0);
            break;
            case 2 : u1 = x * 0.5 - 1.0;
            v1 = y * 0.5 + 1.0;
            z1 = fmod2(VAR(truchet_ae_K21A) * z1 + VAR(truchet_ae_K22A), 1.0);
            z2 = fmod2(VAR(truchet_ae_K21B) * z2 + VAR(truchet_ae_K22B), 0.5);
            break;
            case 3 : u1 = - x * 0.5 - 1.0;
            v1 = - y * 0.5 + 1.0;
            z1 = fmod2(VAR(truchet_ae_K31A) * z1 + VAR(truchet_ae_K32A), 1.0);
            z2 = fmod2(VAR(truchet_ae_K31B) * z2 + VAR(truchet_ae_K32B), 1.0);
            break;
        }
    } else if(VAR(truchet_ae_layout) == 3) {
        switch(i) {
            case 0 : u1 = x * 0.5;
            v1 = y * 0.5;
            z1 = fmod2(VAR(truchet_ae_K01A) * z1 + VAR(truchet_ae_K02A), 1.0);
            z2 = fmod2(VAR(truchet_ae_K01B) * z2 + VAR(truchet_ae_K02B), 1.0);
            break;
            case 1 : u1 = x * 0.5 - 1.0;
            v1 = y * 0.5 + 1.0;
            z1 = fmod2(VAR(truchet_ae_K11A) * z1 + VAR(truchet_ae_K12A), 1.0);
            z2 = fmod2(VAR(truchet_ae_K11B) * z2 + VAR(truchet_ae_K12B), 1.0);
            break;
            case 2 : u1 = - y * 0.5 - 1.0;
            v1 = x * 0.5 - 1.0;
            z1 = fmod2(VAR(truchet_ae_K21A) * z1 + VAR(truchet_ae_K22A), 1.0);
            z2 = fmod2(VAR(truchet_ae_K21B) * z2 + VAR(truchet_ae_K22B), 0.5);
            break;
            case 3 : u1 = y * 0.5 + 1.0;
            v1 = - x * 0.5 + 1.0;
            z1 = fmod2(VAR(truchet_ae_K31A) * z1 + VAR(truchet_ae_K32A), 1.0);
            z2 = fmod2(VAR(truchet_ae_K31B) * z2 + VAR(truchet_ae_K32B), 1.0);
            break;
        }
    } else if(VAR(truchet_ae_layout) == 4) {
        switch(i) {
            case 0 : u1 = x * 0.5 + 1;
            v1 = y * 0.5 + M_SQ3_2;
            z1 = fmod2(VAR(truchet_ae_K01A) * z1 + VAR(truchet_ae_K02A), 1.0);
            z2 = fmod2(VAR(truchet_ae_K01B) * z2 + VAR(truchet_ae_K02B), 1.0);
            break;
            case 1 : u1 = x * 0.5 - 1;
            v1 = y * 0.5 + M_SQ3_2;
            z1 = fmod2(VAR(truchet_ae_K11A) * z1 + VAR(truchet_ae_K12A), 1.0);
            z2 = fmod2(VAR(truchet_ae_K11B) * z2 + VAR(truchet_ae_K12B), 1.0);
            break;
            case 2 : u1 = x * 0.5;
            v1 = y * 0.5 - M_SQ3_2;
            z1 = fmod2(VAR(truchet_ae_K21A) * z1 + VAR(truchet_ae_K22A), 1.0);
            z2 = fmod2(VAR(truchet_ae_K21B) * z2 + VAR(truchet_ae_K22B), 0.5);
            break;
            case 3 : u1 = x * 0.5;
            v1 = - y * 0.5 + M_SQ3_2;
            z1 = fmod2(VAR(truchet_ae_K31A) * z1 + VAR(truchet_ae_K32A), 1.0);
            z2 = fmod2(VAR(truchet_ae_K31B) * z2 + VAR(truchet_ae_K32B), 1.0);
            break;
        }
    } else {
        double j;
        switch(i) {
            case 0 : u1 = x * 0.5 + 1.0;
            v1 = y * 0.5 + 1.0;
            j = v1 + 0.7;
            if(j > 2.) j = j - 2.;
            v1 = j;
            z1 = fmod2(VAR(truchet_ae_K01A) * z1 + VAR(truchet_ae_K02A), 1.0);
            z2 = fmod2(VAR(truchet_ae_K01B) * z2 + VAR(truchet_ae_K02B), 1.0);
            break;
            case 1 : u1 = x * 0.5 - 1.0;
            v1 = y * 0.5 + 1.0;
            z1 = fmod2(VAR(truchet_ae_K11A) * z1 + VAR(truchet_ae_K12A), 1.0);
            z2 = fmod2(VAR(truchet_ae_K11B) * z2 + VAR(truchet_ae_K12B), 1.0);
            break;
            case 2 : u1 = x * 0.5 + 1.0;
            v1 = y * 0.5 - 1.0;
            z1 = fmod2(VAR(truchet_ae_K21A) * z1 + VAR(truchet_ae_K22A), 1.0);
            z2 = fmod2(VAR(truchet_ae_K21B) * z2 + VAR(truchet_ae_K22B), 0.5);
            break;
            case 3 : u1 = x * 0.5 - 1.0;
            v1 = y * 0.5 - 1.0;
            z1 = fmod2(VAR(truchet_ae_K31A) * z1 + VAR(truchet_ae_K32A), 1.0);
            z2 = fmod2(VAR(truchet_ae_K31B) * z2 + VAR(truchet_ae_K32B), 1.0);
            break;
        }
    }
    double uu1 = VAR(truchet_ae_cosang) * u1 - VAR(truchet_ae_sinang) * v1;
    double vv1 = VAR(truchet_ae_sinang) * u1 + VAR(truchet_ae_cosang) * v1;
    int m = (int) floor(uu1 / VAR(truchet_ae_step));
    int n = (int) floor(vv1 / VAR(truchet_ae_step));
    double u = uu1 / VAR(truchet_ae_step) - m;
    double v = vv1 / VAR(truchet_ae_step) - n;
    double chance = dn1((m + 34 * n + VAR(truchet_ae_seed)));
    double cir = 0.0;
    double square = 0.;
    bool inv = false;
    switch(VAR(truchet_ae_style)) {
        case 0 : if(chance > 0.5) {
            if(((v < u + 1 - VAR(truchet_ae_width)) && (v > u + VAR(truchet_ae_width))) || ((v < u - VAR(truchet_ae_width)) && (v > u - 1 + VAR(truchet_ae_width)))) z = z1;
            else z = z2;
        } else {
            if(((v < - u + 1 - VAR(truchet_ae_width)) && (v > - u + VAR(truchet_ae_width))) || ((v > - u + 1 + VAR(truchet_ae_width)) && (v < - u + 2 - VAR(truchet_ae_width)))) z = z1;
            else z = z2;
        }
        break;
        case 1 : square = max(fabs(u - .5), fabs(v - .5)) - 0.5 * (1. - VAR(truchet_ae_width));
        if(chance < 0.25) {
            if(((square < 0) ^ (u > v))) z = z1;
            else z = z2;
        } else if(chance < 0.5) {
            if(((square < 0) ^ (u > 1. - v))) z = z1;
            else z = z2;
        } else if(chance < 0.75) {
            if(((square < 0) ^ (u < v))) z = z1;
            else z = z2;
        } else {
            if(((square < 0) ^ (u < 1. - v))) z = z1;
            else z = z2;
        }
        break;
        case 2 : if(chance < 0.5) {
            cir = sqrt((u - 1.) * (u - 1.) + (v - 1.) * (v - 1.));
            cir = min(cir, sqrt(u * u + v * v));
            cir = fabs(fabs(cir - 0.5) - 0.5) - 0.5 * (1. - VAR(truchet_ae_width));
            if(cir < 0) z = z1;
            else z = z2;
        } else {
            cir = sqrt((u - 1.) * (u - 1.) + v * v);
            cir = min(cir, sqrt(u * u + (v - 1.) * (v - 1.)));
            cir = fabs(fabs(cir - 0.5) - 0.5) - 0.5 * (1. - VAR(truchet_ae_width));
            if(cir < 0) z = z1;
            else z = z2;
        }
        break;
        case 3 : if(chance < 0.333333) {
            cir = sqrt((u - 1.) * (u - 1.) + (v - 1.) * (v - 1.));
            cir = min(cir, sqrt(u * u + v * v));
            cir = fabs(fabs(cir - 0.5) - 0.5) - 0.5 * (1. - VAR(truchet_ae_width));
            if(cir < 0) z = z1;
            else z = z2;
        } else if(chance < 0.666666) {
            cir = sqrt((u - 1.) * (u - 1.) + v * v);
            cir = min(cir, sqrt(u * u + (v - 1.) * (v - 1.)));
            cir = fabs(fabs(cir - 0.5) - 0.5) - 0.5 * (1. - VAR(truchet_ae_width));
            if(cir < 0) z = z1;
            else z = z2;
        } else {
            cir = 0.5 * (VAR(truchet_ae_width)) - min(fabs(u - .5), fabs(v - .5));
            if(cir < 0) z = z1;
            else z = z2;
        }
        break;
        case 4 : square = max(fabs(u - .5), fabs(v - .5)) - 0.5 * (1. - VAR(truchet_ae_width));
        if(chance < 0.125) {
            if(((square < 0) ^ (u > v))) z = z1;
            else z = z2;
        } else if(chance < 0.25) {
            if(((square < 0) ^ (u > 1. - v))) z = z1;
            else z = z2;
        } else if(chance < 0.375) {
            if(((square < 0) ^ (u < v))) z = z1;
            else z = z2;
        } else if(chance < 0.5) {
            if(((square < 0) ^ (u < 1. - v))) z = z1;
            else z = z2;
        } else if(chance < 0.625) {
            if(((square < 0) ^ (u < 0.5))) z = z1;
            else z = z2;
        } else if(chance < 0.75) {
            if(((square < 0) ^ (v < 0.5))) z = z1;
            else z = z2;
        } else if(chance < 0.875) {
            if(((square < 0) ^ (u > 0.5))) z = z1;
            else z = z2;
        } else {
            if(((square < 0) ^ (v > 0.5))) z = z1;
            else z = z2;
        }
        break;
        case 5 : inv = (m % 2 == 0) ^ (n % 2 == 0);
        if(chance < 0.5) {
            cir = sqrt((u - 1.) * (u - 1.) + (v - 1.) * (v - 1.));
            cir = min(cir, sqrt(u * u + v * v));
            square = cir;
            cir = fabs(cir) - 0.5;
            square = min(square, sqrt((u - 1.) * (u - 1.) + v * v));
            square = min(square, sqrt(u * u + (v - 1.) * (v - 1.)));
            square = fabs(square) - VAR(truchet_ae_width);
            if((cir < 0) ^ (square < 0) ^ inv) z = z1;
            else z = z2;
        } else {
            cir = sqrt((u - 1.) * (u - 1.) + v * v);
            cir = min(cir, sqrt(u * u + (v - 1.) * (v - 1.)));
            square = cir;
            cir = fabs(cir) - 0.5;
            square = min(square, sqrt((u - 1.) * (u - 1.) + (v - 1.) * (v - 1.)));
            square = min(square, sqrt(u * u + v * v));
            square = fabs(square) - VAR(truchet_ae_width);
            if((cir < 0) ^ (square < 0) ^ inv) z = z2;
            else z = z1;
        }
        break;
    }
    x = u1;
    y = v1;
    FPx += u1;
    FPy += v1;
    
    TC = z;
    z1 = z;
    z2 = z;
    return TRUE;
}
