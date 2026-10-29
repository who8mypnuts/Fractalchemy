/*
    Fractalchemy formula library — translated from the JWildfire variation
        RecurrencePlotFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

// keeps a private orbit between points (JWildfire fields updated per point): the statics below
typedef struct {
    double recurrenceplot_a;
    double recurrenceplot_b;
    double recurrenceplot_Density;
    int recurrenceplot_func_id;
    int recurrenceplot_k;
    double recurrenceplot_scale;
    double recurrenceplot_angle;
    double recurrenceplot_offset;
    double recurrenceplot_tolerance;
    int recurrenceplot_dc;
    double recurrenceplot_ldcs;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("recurrenceplot");

APO_VARIABLES(
    VAR_INTEGER(recurrenceplot_func_id, 0),
    VAR_REAL(recurrenceplot_a, 0.5),
    VAR_REAL(recurrenceplot_b, 10),
    VAR_INTEGER(recurrenceplot_k, 5),
    VAR_REAL(recurrenceplot_Density, 700),
    VAR_INTEGER(recurrenceplot_dc, 0),
    VAR_REAL(recurrenceplot_scale, 1),
    VAR_REAL(recurrenceplot_angle, 0),
    VAR_REAL(recurrenceplot_offset, 0),
    VAR_REAL(recurrenceplot_tolerance, 5)
);

static double y1 = 0;
static double y2 = 0;
static double oldx = 0;
static double oldy = 0;

double F6(int i)
{
    double Summe = 0;
    Summe = VAR(recurrenceplot_a) / (1 + exp(- VAR(recurrenceplot_b) * (i - VAR(recurrenceplot_Density) / 2.0) / VAR(recurrenceplot_Density)));
    return Summe;
}

double F22(int i, int b)
{
    double Sum = 0, x;
    x = (2.0 * i) / VAR(recurrenceplot_Density) - 1;
    switch(b) {
        case 0 : Sum = VAR(recurrenceplot_a);
        break;
        case 1 : Sum = VAR(recurrenceplot_a) * x;
        break;
        case 2 : Sum = VAR(recurrenceplot_a) * (3.0 * pow(x, 2) - 1.0) / 2.0;
        break;
        case 3 : Sum = VAR(recurrenceplot_a) * (5.0 * pow(x, 3) - 3.0 * x) / 2.0;
        break;
        case 4 : Sum = VAR(recurrenceplot_a) * (35.0 * pow(x, 4) - 30.0 * pow(x, 2) + 3) / 8.0;
        break;
        case 5 : Sum = VAR(recurrenceplot_a) * (63.0 * pow(x, 5) - 70.0 * pow(x, 3) + 15.0 * x) / 8.0;
        break;
        case 6 : Sum = VAR(recurrenceplot_a) * (231.0 * pow(x, 6) - 315.0 * pow(x, 4) + 105.0 * pow(x, 2) - 5) / 16.0;
        break;
        case 7 : Sum = VAR(recurrenceplot_a) * (429.0 * pow(x, 7) - 693.0 * pow(x, 5) + 315.0 * pow(x, 3) - 35.0 * x) / 16.0;
        break;
        case 8 : Sum = VAR(recurrenceplot_a) * (6435.0 * pow(x, 8) - 12012.0 * pow(x, 6) + 6930.0 * pow(x, 4) - 1260.0 * pow(x, 2) + 35) / 128.0;
        break;
        case 9 : Sum = VAR(recurrenceplot_a) * (12155.0 * pow(x, 9) - 25740.0 * pow(x, 7) + 18018.0 * pow(x, 5) - 4620.0 * pow(x, 3) + 315.0 * x) / 128.0;
        break;
        case 10 : Sum = VAR(recurrenceplot_a) * (46189.0 * pow(x, 10) - 109395.0 * pow(x, 8) + 90090.0 * pow(x, 6) - 30030.0 * pow(x, 4) + 3465.0 * pow(x, 2) - 63) / 256.0;
        break;
    }
    return Sum;
}

double F23(int i, int k)
{
    double j;
    double Summe = 0;
    for(j = 1;
    j <= k;
    j++) {
        Summe = Summe + sin(i * (2 * j - 1) * VAR(recurrenceplot_b) * 2 * M_PI / (VAR(recurrenceplot_Density))) / (2 * j - 1);
    }
    Summe = Summe * (4 * VAR(recurrenceplot_a) / M_PI);
    return Summe;
}

double F24(int i, int k)
{
    double j;
    double Summe = 0;
    for(j = 1;
    j <= k;
    j++) {
        Summe = Summe + sin(i * j * VAR(recurrenceplot_b) * 2 * M_PI / (VAR(recurrenceplot_Density))) / j;
    }
    Summe = Summe * (- 2 * VAR(recurrenceplot_a) / M_PI);
    return Summe;
}

double F25(int i, int k)
{
    double j;
    double Summe = 0;
    for(j = 1;
    j <= k;
    j++) {
        Summe = Summe + cos(i * (2 * j) * VAR(recurrenceplot_b) * 2 * M_PI / (VAR(recurrenceplot_Density))) / ((2 * j - 1) * (2 * j + 1));
    }
    Summe = (4 * VAR(recurrenceplot_a) / M_PI) * (0.5 - Summe);
    return Summe;
}

double F26(int i, int k)
{
    double j;
    double Summe = 0;
    for(j = 1;
    j <= k;
    j++) {
        Summe = Summe + pow(- 1.0, j) * cos((i) * (2 * j) * VAR(recurrenceplot_b) * 1 * M_PI / (VAR(recurrenceplot_Density))) / (j * j);
    }
    Summe = (VAR(recurrenceplot_a) * M_PI * M_PI / 3.0) + 4.0 * VAR(recurrenceplot_a) * Summe;
    return Summe;
}

double F27(int i)
{
    double Sinc = 0;
    Sinc = VAR(recurrenceplot_a) * sin(VAR(recurrenceplot_b) * M_PI * (i - 0.5 * VAR(recurrenceplot_Density)) / VAR(recurrenceplot_Density)) / (VAR(recurrenceplot_b) * M_PI * (i - 0.5 * VAR(recurrenceplot_Density)) / VAR(recurrenceplot_Density));
    return Sinc;
}

double F28(int i)
{
    double Gabor = 0;
    Gabor = VAR(recurrenceplot_a) * exp(- VAR(recurrenceplot_b) * (((i - 0.5 * VAR(recurrenceplot_Density)) / VAR(recurrenceplot_Density)) * (i - 0.5 * VAR(recurrenceplot_Density)) / VAR(recurrenceplot_Density))) * cos(2.0 * VAR(recurrenceplot_k) * M_PI * i / VAR(recurrenceplot_Density));
    return Gabor;
}

double F29(int i, int b)
{
    double Summe, x;
    x = (2.0 * i) / VAR(recurrenceplot_Density) - 1;
    Summe = 0.0;
    switch(b) {
        case 0 : Summe = VAR(recurrenceplot_a);
        break;
        case 1 : Summe = VAR(recurrenceplot_a) * x;
        break;
        case 2 : Summe = VAR(recurrenceplot_a) * (2.0 * pow(x, 2) - 1.0);
        break;
        case 3 : Summe = VAR(recurrenceplot_a) * (4.0 * pow(x, 3) - 3.0 * x);
        break;
        case 4 : Summe = VAR(recurrenceplot_a) * (8.0 * pow(x, 4) - 8.0 * pow(x, 2) + 1);
        break;
        case 5 : Summe = VAR(recurrenceplot_a) * (16.0 * pow(x, 5) - 20.0 * pow(x, 3) + 5.0 * x);
        break;
        case 6 : Summe = VAR(recurrenceplot_a) * (32.0 * pow(x, 6) - 48.0 * pow(x, 4) + 18.0 * pow(x, 2) - 1);
        break;
        case 7 : Summe = VAR(recurrenceplot_a) * (64.0 * pow(x, 7) - 112.0 * pow(x, 5) + 56.0 * pow(x, 3) - 7.0 * x);
        break;
        case 8 : Summe = VAR(recurrenceplot_a) * (128.0 * pow(x, 8) - 256.0 * pow(x, 6) + 160.0 * pow(x, 4) - 32.0 * pow(x, 2) + 1);
        break;
        case 9 : Summe = VAR(recurrenceplot_a) * (256.0 * pow(x, 9) - 576.0 * pow(x, 7) + 432.0 * pow(x, 5) - 120.0 * pow(x, 3) + 9.0 * x);
        break;
        case 10 : Summe = VAR(recurrenceplot_a) * (512.0 * pow(x, 10) - 1280.0 * pow(x, 8) + 1120.0 * pow(x, 6) - 400.0 * pow(x, 4) + 50.0 * pow(x, 2) - 1);
        break;
        case 11 : Summe = VAR(recurrenceplot_a) * (1024.0 * pow(x, 11) - 2816.0 * pow(x, 9) + 2816.0 * pow(x, 7) - 1232.0 * pow(x, 5) + 220.0 * pow(x, 3) - 11.0 * x);
        break;
        case 12 : Summe = VAR(recurrenceplot_a) * (2048.0 * pow(x, 12) - 6144.0 * pow(x, 10) + 6912.0 * pow(x, 8) - 3584.0 * pow(x, 6) + 840.0 * pow(x, 4) - 72.0 * pow(x, 2) + 1);
        break;
    }
    return Summe;
}

int PluginVarPrepare(Variation* vp)
{
    VAR(recurrenceplot_ldcs) = 1.0 / (VAR(recurrenceplot_scale) == 0.0 ? 10E-6 : VAR(recurrenceplot_scale));
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    int i, j;
    double dist, x, y;
    i = (int)((VAR(recurrenceplot_Density)) * random01());
    j = (int)((VAR(recurrenceplot_Density)) * random01());
    if(VAR(recurrenceplot_func_id) == 0) {
        y1 = 50 * sin(i * 4 * M_PI / (1 * VAR(recurrenceplot_Density))) + 25 * sin(i * 40 * M_PI / (1 * VAR(recurrenceplot_Density)));
        y2 = 50 * sin(j * 4 * M_PI / (1 * VAR(recurrenceplot_Density))) + 25 * sin(j * 40 * M_PI / (1 * VAR(recurrenceplot_Density)));
    } else if(VAR(recurrenceplot_func_id) == 1) {
        y1 = 10 * sin(i * 5 * M_PI / (1 * VAR(recurrenceplot_Density))) * 5 * sin(i * 15 * M_PI / (1 * VAR(recurrenceplot_Density)));
        y2 = 10 * sin(j * 5 * M_PI / (1 * VAR(recurrenceplot_Density))) * 5 * sin(j * 15 * M_PI / (1 * VAR(recurrenceplot_Density)));
    } else if(VAR(recurrenceplot_func_id) == 2) {
        y1 = 50 * cos(i * 24 * M_PI / (1 * VAR(recurrenceplot_Density)) + 5 * sin(i * 6 * M_PI / (1 * VAR(recurrenceplot_Density))));
        y2 = 50 * cos(j * 24 * M_PI / (1 * VAR(recurrenceplot_Density)) + 5 * sin(j * 6 * M_PI / (1 * VAR(recurrenceplot_Density))));
    } else if(VAR(recurrenceplot_func_id) == 3) {
        y1 = 50 * sin(i * 20 * M_PI / (1 * VAR(recurrenceplot_Density))) + 50 * sin(i * 22 * M_PI / (1 * VAR(recurrenceplot_Density)) + M_PI);
        y2 = 50 * sin(j * 20 * M_PI / (1 * VAR(recurrenceplot_Density))) + 50 * sin(j * 22 * M_PI / (1 * VAR(recurrenceplot_Density)) + M_PI);
    } else if(VAR(recurrenceplot_func_id) == 4) {
        y1 = 50 * sin(i * 20 * M_PI / (1 * VAR(recurrenceplot_Density))) + 10 * sin(i * 22 * M_PI / (1 * VAR(recurrenceplot_Density)));
        y2 = 50 * sin(j * 20 * M_PI / (1 * VAR(recurrenceplot_Density))) + 10 * sin(j * 22 * M_PI / (1 * VAR(recurrenceplot_Density)));
    } else if(VAR(recurrenceplot_func_id) == 5) {
        y1 = 50 * sin(i * VAR(recurrenceplot_a) * M_PI / (1 * VAR(recurrenceplot_Density)) + 1 * sin(i * VAR(recurrenceplot_a) * M_PI / (1 * VAR(recurrenceplot_Density))));
        y2 = 50 * sin(j * VAR(recurrenceplot_a) * M_PI / (1 * VAR(recurrenceplot_Density)) + 1 * sin(j * VAR(recurrenceplot_a) * M_PI / (1 * VAR(recurrenceplot_Density))));
    } else if(VAR(recurrenceplot_func_id) == 6) {
        y1 = F6(i);
        y2 = F6(j);
    } else if(VAR(recurrenceplot_func_id) == 7) {
        y1 = (400 / M_PI) * (sin(i * M_PI / (0.5 * VAR(recurrenceplot_Density))) + sin(i * 3 * M_PI / (0.5 * VAR(recurrenceplot_Density))) / 3.0 + sin(i * 5 * M_PI / (0.5 * VAR(recurrenceplot_Density))) / 5.0 + sin(i * 7 * M_PI / (0.5 * VAR(recurrenceplot_Density))) / 7.0);
        y2 = (400 / M_PI) * (sin(j * M_PI / (0.5 * VAR(recurrenceplot_Density))) + sin(j * 3 * M_PI / (0.5 * VAR(recurrenceplot_Density))) / 3.0 + sin(j * 5 * M_PI / (0.5 * VAR(recurrenceplot_Density))) / 5.0 + sin(j * 7 * M_PI / (0.5 * VAR(recurrenceplot_Density))) / 7.0);
    } else if(VAR(recurrenceplot_func_id) == 8) {
        y1 = (400 / M_PI * M_PI) * (sin(i * M_PI / (0.5 * VAR(recurrenceplot_Density))) - sin(i * 3 * M_PI / (0.5 * VAR(recurrenceplot_Density))) / 9.0 + sin(i * 5 * M_PI / (0.5 * VAR(recurrenceplot_Density))) / 25.0 - sin(i * 7 * M_PI / (0.5 * VAR(recurrenceplot_Density))) / 49.0);
        y2 = (400 / M_PI * M_PI) * (sin(j * M_PI / (0.5 * VAR(recurrenceplot_Density))) - sin(j * 3 * M_PI / (0.5 * VAR(recurrenceplot_Density))) / 9.0 + sin(j * 5 * M_PI / (0.5 * VAR(recurrenceplot_Density))) / 25.0 - sin(j * 7 * M_PI / (0.5 * VAR(recurrenceplot_Density))) / 49.0);
    } else if(VAR(recurrenceplot_func_id) == 9) {
        y1 = tanh(VAR(recurrenceplot_a) * i * M_PI / VAR(recurrenceplot_Density));
        y2 = tanh(VAR(recurrenceplot_a) * j * M_PI / VAR(recurrenceplot_Density));
    } else if(VAR(recurrenceplot_func_id) == 10) {
        y1 = tan(VAR(recurrenceplot_a) * i * M_PI / VAR(recurrenceplot_Density));
        y2 = tan(VAR(recurrenceplot_a) * j * M_PI / VAR(recurrenceplot_Density));
    } else if(VAR(recurrenceplot_func_id) == 11) {
        y1 = (- 200 / M_PI) * (sin(i * M_PI / (0.5 * VAR(recurrenceplot_Density))) + sin(i * 2 * M_PI / (0.5 * VAR(recurrenceplot_Density))) / 2.0 + sin(i * 3 * M_PI / (0.5 * VAR(recurrenceplot_Density))) / 3.0 + sin(i * 4 * M_PI / (0.5 * VAR(recurrenceplot_Density))) / 4.0 + sin(i * 5 * M_PI / (0.5 * VAR(recurrenceplot_Density))) / 5.0 + sin(i * 6 * M_PI / (0.5 * VAR(recurrenceplot_Density))) / 6.0 + sin(i * 7 * M_PI / (0.5 * VAR(recurrenceplot_Density))) / 7.0 + sin(i * 8 * M_PI / (0.5 * VAR(recurrenceplot_Density))) / 8.0);
        y2 = (- 200 / M_PI) * (sin(j * M_PI / (0.5 * VAR(recurrenceplot_Density))) + sin(j * 2 * M_PI / (0.5 * VAR(recurrenceplot_Density))) / 2.0 + sin(j * 3 * M_PI / (0.5 * VAR(recurrenceplot_Density))) / 3.0 + sin(j * 4 * M_PI / (0.5 * VAR(recurrenceplot_Density))) / 4.0 + sin(j * 5 * M_PI / (0.5 * VAR(recurrenceplot_Density))) / 5.0 + sin(j * 6 * M_PI / (0.5 * VAR(recurrenceplot_Density))) / 6.0 + sin(j * 7 * M_PI / (0.5 * VAR(recurrenceplot_Density))) / 7.0 + sin(j * 8 * M_PI / (0.5 * VAR(recurrenceplot_Density))) / 8.0);
    } else if(VAR(recurrenceplot_func_id) == 12) {
        y1 = 50 * sin(i * 40 * M_PI / (1 * VAR(recurrenceplot_Density))) + 50 * sin(i * 44 * M_PI / (1.0 * VAR(recurrenceplot_Density)));
        y2 = 50 * sin(j * 40 * M_PI / (1 * VAR(recurrenceplot_Density))) + 50 * sin(j * 44 * M_PI / (1.0 * VAR(recurrenceplot_Density)));
    } else if(VAR(recurrenceplot_func_id) == 13) {
        y1 = 50 * sin(i * 40 * M_PI / (1 * VAR(recurrenceplot_Density))) + 50 * sin(i * 44 * M_PI / (1.0 * VAR(recurrenceplot_Density)) + M_PI);
        y2 = 50 * sin(j * 40 * M_PI / (1 * VAR(recurrenceplot_Density))) + 50 * sin(j * 44 * M_PI / (1.0 * VAR(recurrenceplot_Density)) + M_PI);
    } else if(VAR(recurrenceplot_func_id) == 14) {
        y1 = 100 * sin(i * 16 * M_PI / (1 * VAR(recurrenceplot_Density))) - 500 + i * 0.25;
        y2 = 100 * sin(j * 16 * M_PI / (1 * VAR(recurrenceplot_Density))) - 500 + j * 0.25;
    } else if(VAR(recurrenceplot_func_id) == 15) {
        y1 = 100 * sin(i * 16 * M_PI / (1 * VAR(recurrenceplot_Density)));
        y2 = 100 * sin(j * 16 * M_PI / (1 * VAR(recurrenceplot_Density)));
    } else if(VAR(recurrenceplot_func_id) == 16) {
        y1 = 1.0 / cos(i * VAR(recurrenceplot_a) * M_PI / VAR(recurrenceplot_Density));
        y2 = 1.0 / cos(j * VAR(recurrenceplot_a) * M_PI / VAR(recurrenceplot_Density));
    } else if(VAR(recurrenceplot_func_id) == 17) {
        y1 = 50 * cos(i * 2 * M_PI * 25 / (1 * VAR(recurrenceplot_Density)) + 25 * sin(i * 2 * M_PI * 0.50 / (1 * VAR(recurrenceplot_Density))));
        y2 = 50 * cos(j * 2 * M_PI * 25 / (1 * VAR(recurrenceplot_Density)) + 25 * sin(j * 2 * M_PI * 0.50 / (1 * VAR(recurrenceplot_Density))));
    } else if(VAR(recurrenceplot_func_id) == 18) {
        y1 = VAR(recurrenceplot_a) * exp(- VAR(recurrenceplot_b) * (2.0 * VAR(recurrenceplot_a) * i / VAR(recurrenceplot_Density) - VAR(recurrenceplot_a)) * (2.0 * VAR(recurrenceplot_a) * i / VAR(recurrenceplot_Density) - VAR(recurrenceplot_a)));
        y2 = VAR(recurrenceplot_a) * exp(- VAR(recurrenceplot_b) * (2.0 * VAR(recurrenceplot_a) * j / VAR(recurrenceplot_Density) - VAR(recurrenceplot_a)) * (2.0 * VAR(recurrenceplot_a) * j / VAR(recurrenceplot_Density) - VAR(recurrenceplot_a)));
    } else if(VAR(recurrenceplot_func_id) == 19) {
        y1 = 500 * sin(i * 10 * M_PI / (VAR(recurrenceplot_Density))) * exp(- 5.0 * i / VAR(recurrenceplot_Density));
        y2 = 500 * sin(j * 10 * M_PI / (VAR(recurrenceplot_Density))) * exp(- 5.0 * j / VAR(recurrenceplot_Density));
    } else if(VAR(recurrenceplot_func_id) == 20) {
        y1 = 500 * sin(i * 20 * M_PI / (VAR(recurrenceplot_Density))) * exp(- 3.0 * i / VAR(recurrenceplot_Density));
        y2 = 500 * sin(j * 20 * M_PI / (VAR(recurrenceplot_Density))) * exp(- 3.0 * j / VAR(recurrenceplot_Density));
    } else if(VAR(recurrenceplot_func_id) == 21) {
        y1 = 50 * tan(i * 2 * M_PI / (1 * VAR(recurrenceplot_Density)));
        y2 = 50 * tan(j * 2 * M_PI / (1 * VAR(recurrenceplot_Density)));
    } else if(VAR(recurrenceplot_func_id) == 22) {
        y1 = F22(i, (int) VAR(recurrenceplot_b));
        y2 = F22(j, (int) VAR(recurrenceplot_b));
    } else if(VAR(recurrenceplot_func_id) == 23) {
        y1 = F23(i, VAR(recurrenceplot_k));
        y2 = F23(j, VAR(recurrenceplot_k));
    } else if(VAR(recurrenceplot_func_id) == 24) {
        y1 = F24(i, VAR(recurrenceplot_k));
        y2 = F24(j, VAR(recurrenceplot_k));
    } else if(VAR(recurrenceplot_func_id) == 25) {
        y1 = F25(i, VAR(recurrenceplot_k));
        y2 = F25(j, VAR(recurrenceplot_k));
    } else if(VAR(recurrenceplot_func_id) == 26) {
        y1 = F26(i, VAR(recurrenceplot_k));
        y2 = F26(j, VAR(recurrenceplot_k));
    } else if(VAR(recurrenceplot_func_id) == 27) {
        y1 = F27(i);
        y2 = F27(j);
    } else if(VAR(recurrenceplot_func_id) == 28) {
        y1 = F28(i);
        y2 = F28(j);
    } else if(VAR(recurrenceplot_func_id) == 29) {
        y1 = F29(i, VAR(recurrenceplot_k));
        y2 = F29(j, VAR(recurrenceplot_k));
    }
    dist = sqrt((y1 - y2) * (y1 - y2));
    if(dist < VAR(recurrenceplot_tolerance)) {
        x = i / VAR(recurrenceplot_Density) - 0.5;
        y = j / VAR(recurrenceplot_Density) - 0.5;
        FPx += VVAR * (x);
        FPy += VVAR * (y);
        oldx = FPx;
        oldy = FPy;
        if(VAR(recurrenceplot_dc) != 0) {
            double s = sin(VAR(recurrenceplot_angle));
            double c = cos(VAR(recurrenceplot_angle));
            if(VAR(recurrenceplot_dc) == 1) TC = fmod(fabs(0.5 * VAR(recurrenceplot_ldcs) * FPx * FPy + VAR(recurrenceplot_offset)), 1.0);
            if(VAR(recurrenceplot_dc) == 2) TC = fmod(fabs(0.5 * (VAR(recurrenceplot_ldcs) * ((c * FPx + s * FPy + VAR(recurrenceplot_offset))) + 1.0)), 1.0);
        }
    } else {
        FPx = oldx;
        FPy = oldy;
    }
    return TRUE;
}
