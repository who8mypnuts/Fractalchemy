/*
    Fractalchemy formula library — translated from the JWildfire variation
        DCGnarlyFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

// keeps a private orbit between points (JWildfire fields updated per point): the statics below
typedef struct {
    int dc_gnarly_mode;
    double dc_gnarly_scalex;
    double dc_gnarly_scaley;
    double dc_gnarly_freqx1;
    double dc_gnarly_freqy1;
    double dc_gnarly_freqx2;
    double dc_gnarly_freqy2;
    double dc_gnarly_freqx3;
    double dc_gnarly_freqy3;
    int dc_gnarly_dc;
    double dc_gnarly_color1;
    double dc_gnarly_color2;
    double dc_gnarly_fmag;
    double dc_gnarly_distort;
    double dc_gnarly_blur;
    double dc_gnarly_scale_z;
    double dc_gnarly_offset_z;
    int dc_gnarly_reset_z;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("dc_gnarly");

APO_VARIABLES(
    VAR_INTEGER(dc_gnarly_mode, 1),
    VAR_REAL(dc_gnarly_scalex, 0.05),
    VAR_REAL(dc_gnarly_scaley, 0.05),
    VAR_REAL(dc_gnarly_freqx1, 3.5),
    VAR_REAL(dc_gnarly_freqy1, 3.5),
    VAR_REAL(dc_gnarly_freqx2, 2),
    VAR_REAL(dc_gnarly_freqy2, 2),
    VAR_REAL(dc_gnarly_freqx3, 5),
    VAR_REAL(dc_gnarly_freqy3, 5),
    VAR_INTEGER(dc_gnarly_dc, 1),
    VAR_REAL(dc_gnarly_color1, 5),
    VAR_REAL(dc_gnarly_color2, 5),
    VAR_REAL(dc_gnarly_fmag, 1),
    VAR_REAL(dc_gnarly_distort, 0),
    VAR_REAL(dc_gnarly_blur, 5),
    VAR_REAL(dc_gnarly_scale_z, 0),
    VAR_REAL(dc_gnarly_offset_z, 0),
    VAR_INTEGER(dc_gnarly_reset_z, 0)
);

static int gauss_N = 0;

double asinh(double x)
{
    return log(x + sqrt(x * x + 1.0));
}

int PluginVarPrepare(Variation* vp)
{
    double gauss_rnd[6];
    gauss_rnd[0] = random01();
    gauss_rnd[1] = random01();
    gauss_rnd[2] = random01();
    gauss_rnd[3] = random01();
    gauss_rnd[4] = random01();
    gauss_rnd[5] = random01();
    gauss_N = 0;
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double gauss_rnd[6];
    double x0 = FTx;
    double y0 = FTy;
    if(VAR(dc_gnarly_blur) > 0) {
        double r = random01() * 2 * M_PI;
        double sina = sin(r);
        double cosa = cos(r);
        r = VAR(dc_gnarly_blur) * (gauss_rnd[0] + gauss_rnd[1] + gauss_rnd[2] + gauss_rnd[3] + gauss_rnd[4] + gauss_rnd[5] - 3);
        gauss_rnd[gauss_N] = random01();
        gauss_N = (gauss_N + 1) & 5;
        x0 += r * cosa;
        y0 += r * sina;
    } else if(VAR(dc_gnarly_blur) < 0) {
        x0 += random01() * VAR(dc_gnarly_blur) * 2 - VAR(dc_gnarly_blur);
        y0 += random01() * VAR(dc_gnarly_blur) * 2 - VAR(dc_gnarly_blur);
    }
    double x1, y1;
    switch(VAR(dc_gnarly_mode)) {
        case 1 : x1 = cos(VAR(dc_gnarly_freqx1) * y0 + sin(VAR(dc_gnarly_freqx2) * (y0 + sin(VAR(dc_gnarly_freqx3) * y0)))) * VAR(dc_gnarly_scalex);
        y1 = cos(VAR(dc_gnarly_freqy1) * x0 + sin(VAR(dc_gnarly_freqy2) * (x0 + sin(VAR(dc_gnarly_freqy3) * x0)))) * VAR(dc_gnarly_scaley);
        break;
        case 2 : x1 = sin(VAR(dc_gnarly_freqx1) * y0 + sin(VAR(dc_gnarly_freqx2) * (y0 + cos(VAR(dc_gnarly_freqx3) * y0)))) * VAR(dc_gnarly_scalex);
        y1 = sin(VAR(dc_gnarly_freqy1) * x0 + sin(VAR(dc_gnarly_freqy2) * (x0 + cos(VAR(dc_gnarly_freqy3) * x0)))) * VAR(dc_gnarly_scaley);
        break;
        case 3 : x1 = cos(VAR(dc_gnarly_freqx1) * y0 + sin(VAR(dc_gnarly_freqx2) * (x0 + sin(VAR(dc_gnarly_freqx3) * y0)))) * VAR(dc_gnarly_scalex);
        y1 = cos(VAR(dc_gnarly_freqy1) * x0 + sin(VAR(dc_gnarly_freqy2) * (y0 + sin(VAR(dc_gnarly_freqy3) * x0)))) * VAR(dc_gnarly_scaley);
        break;
        case 4 : x1 = sin(VAR(dc_gnarly_freqx1) * y0 + sin(sqrt(fabs(VAR(dc_gnarly_freqx2) * (y0 + cos(VAR(dc_gnarly_freqx3) * y0)))))) * VAR(dc_gnarly_scalex);
        y1 = sin(VAR(dc_gnarly_freqy1) * x0 + sin(sqrt(fabs(VAR(dc_gnarly_freqy2) * (x0 + cos(VAR(dc_gnarly_freqy3) * x0)))))) * VAR(dc_gnarly_scaley);
        break;
        case 5 : x1 = cos(VAR(dc_gnarly_freqx1) * y0 + asinh(VAR(dc_gnarly_freqx2) * (y0 + sin(VAR(dc_gnarly_freqx3) * y0)))) * VAR(dc_gnarly_scalex);
        y1 = cos(VAR(dc_gnarly_freqy1) * x0 + asinh(VAR(dc_gnarly_freqy2) * (x0 + sin(VAR(dc_gnarly_freqy3) * x0)))) * VAR(dc_gnarly_scaley);
        break;
        case 6 : x1 = cos(VAR(dc_gnarly_freqx1) * y0 + tan(VAR(dc_gnarly_freqx2) * (y0 + sin(VAR(dc_gnarly_freqx3) * y0)))) * VAR(dc_gnarly_scalex);
        y1 = cos(VAR(dc_gnarly_freqy1) * x0 + tan(VAR(dc_gnarly_freqy2) * (x0 + sin(VAR(dc_gnarly_freqy3) * x0)))) * VAR(dc_gnarly_scaley);
        break;
        case 7 : x1 = sin(VAR(dc_gnarly_freqx1) * y0 + sin(sqr(VAR(dc_gnarly_freqx2) * (y0 + cos(VAR(dc_gnarly_freqx3) * y0))))) * VAR(dc_gnarly_scalex);
        y1 = sin(VAR(dc_gnarly_freqy1) * x0 + sin(sqr(VAR(dc_gnarly_freqy2) * (x0 + cos(VAR(dc_gnarly_freqy3) * x0))))) * VAR(dc_gnarly_scaley);
        break;
        case 8 : x1 = sin(VAR(dc_gnarly_freqx1) * y0 + sin(sqr(VAR(dc_gnarly_freqx2) * (x0 + cos(VAR(dc_gnarly_freqx3) * y0))))) * VAR(dc_gnarly_scalex);
        y1 = sin(VAR(dc_gnarly_freqy1) * x0 + sin(sqr(VAR(dc_gnarly_freqy2) * (y0 + cos(VAR(dc_gnarly_freqy3) * x0))))) * VAR(dc_gnarly_scaley);
        break;
        default : x1 = sin(VAR(dc_gnarly_freqx1) * y0) * VAR(dc_gnarly_scalex);
        y1 = sin(VAR(dc_gnarly_freqy1) * x0) * VAR(dc_gnarly_scaley);
        break;
    }
    double s1 = log(sqrt(sqr(x1) + sqr(y1))) * VAR(dc_gnarly_distort);
    FPx += VVAR * (x0 + x1) / 2;
    FPy += VVAR * (y0 + y1) / 2;
    if(VAR(dc_gnarly_dc) != 0) {
        TC = fmod(fabs(cos(x0 + x1 * VAR(dc_gnarly_color1) + s1) + sin(y0 + y1 * VAR(dc_gnarly_color2) + s1)), VAR(dc_gnarly_fmag));
    }
    double dz = TC * VAR(dc_gnarly_scale_z) + VAR(dc_gnarly_offset_z);
    if(VAR(dc_gnarly_reset_z) > 0) {
        FPz = dz;
    } else {
        FPz += dz;
    }
    return TRUE;
}
