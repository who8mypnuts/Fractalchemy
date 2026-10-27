/*
    Fractalchemy formula library — post_falloff2
    Ported by hand from falloff2.c (Apophysis 7X src/Plugin, Georg Kiehne "Xyrus02", GPL v2+;
    "partially adapted from the falloff variation of MetaCore"): the double3/double4 structs of
    the original are written out as scalars, which is all that changed.
    Mode: post (rewrites the accumulated point)
*/

typedef struct {
    double post_falloff2_scatter;
    double post_falloff2_mindist;
    double post_falloff2_mul_x;
    double post_falloff2_mul_y;
    double post_falloff2_mul_z;
    double post_falloff2_mul_c;
    double post_falloff2_x0;
    double post_falloff2_y0;
    double post_falloff2_z0;
    int post_falloff2_invert;
    int post_falloff2_type;
    double r_max, d_0;
} Variables;

#include "apoplugin.h"

#define random_double (random01() - 0.5)
#define mind(x, x0) ((x) < (x0) ? (x0) : (x))
#define scatter_adjust 0.04

APO_PLUGIN("post_falloff2");
APO_VARIABLES(
    VAR_REAL_RANGE(post_falloff2_scatter, EPS, DBL_MAX, 1.0),
    VAR_REAL_RANGE(post_falloff2_mindist, 0.0, DBL_MAX, 0.5),
    VAR_REAL_RANGE(post_falloff2_mul_x, 0.0, 1.0, 1.0),
    VAR_REAL_RANGE(post_falloff2_mul_y, 0.0, 1.0, 1.0),
    VAR_REAL_RANGE(post_falloff2_mul_z, 0.0, 1.0, 0.0),
    VAR_REAL_RANGE(post_falloff2_mul_c, 0.0, 1.0, 0.0),
    VAR_REAL(post_falloff2_x0, 0.0),
    VAR_REAL(post_falloff2_y0, 0.0),
    VAR_REAL(post_falloff2_z0, 0.0),
    VAR_INTEGER_RANGE(post_falloff2_invert, 0, 1, 0),
    VAR_INTEGER_RANGE(post_falloff2_type, 0, 2, 0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(r_max) = scatter_adjust * VAR(post_falloff2_scatter);
    VAR(d_0) = VAR(post_falloff2_mindist);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    const double in_x = FPx, in_y = FPy, in_z = FPz, in_c = TC;
    const double mul_x = VAR(post_falloff2_mul_x), mul_y = VAR(post_falloff2_mul_y), mul_z = VAR(post_falloff2_mul_z), mul_c = VAR(post_falloff2_mul_c);
    const double rnd_x = random_double, rnd_y = random_double, rnd_z = random_double, rnd_c = random_double;

    const double dist_a = sqrt(sqr(in_x - VAR(post_falloff2_x0)) + sqr(in_y - VAR(post_falloff2_y0)) + sqr(in_z - VAR(post_falloff2_z0)));
    const double dist_b = VAR(post_falloff2_invert) != 0 ? mind(1 - dist_a, 0) : mind(dist_a, 0);
    const double dist = mind((dist_b - VAR(d_0)) * VAR(r_max), 0);

    double out_x, out_y, out_z, out_c;
    if (VAR(post_falloff2_type) == 1) {
        // radial
        if (in_x == 0 && in_y == 0 && in_z == 0) {
            out_x = in_x; out_y = in_y; out_z = in_z; out_c = in_c;
        } else {
            const double r_in = sqrt(sqr(in_x) + sqr(in_y) + sqr(in_z));
            const double sigma = asin(in_z / r_in) + mul_z * rnd_z * dist;
            const double phi = atan2(in_y, in_x) + mul_y * rnd_y * dist;
            const double r = r_in + mul_x * rnd_x * dist;
            double sigma_s, sigma_c; fsincos(sigma, &sigma_s, &sigma_c);
            double phi_s, phi_c; fsincos(phi, &phi_s, &phi_c);
            out_x = r * sigma_c * phi_c;
            out_y = r * sigma_c * phi_s;
            out_z = r * sigma_s;
            out_c = in_c + mul_c * rnd_c * dist;
        }
    } else if (VAR(post_falloff2_type) == 2) {
        // gaussian
        const double sigma = dist * rnd_y * M_2PI;
        const double phi = dist * rnd_z * M_PI;
        const double rad = dist * rnd_x;
        double sigma_s, sigma_c; fsincos(sigma, &sigma_s, &sigma_c);
        double phi_s, phi_c; fsincos(phi, &phi_s, &phi_c);
        out_x = in_x + mul_x * rad * sigma_c * phi_c;
        out_y = in_y + mul_y * rad * sigma_c * phi_s;
        out_z = in_z + mul_z * rad * sigma_s;
        out_c = in_c + mul_c * dist * rnd_c;
    } else {
        // linear
        out_x = in_x + mul_x * rnd_x * dist;
        out_y = in_y + mul_y * rnd_y * dist;
        out_z = in_z + mul_z * rnd_z * dist;
        out_c = in_c + mul_c * rnd_c * dist;
    }

    FPx = out_x * VVAR;
    FPy = out_y * VVAR;
    FPz = out_z * VVAR;
    TC = fabs(fmod(out_c, 1.0));
    return TRUE;
}
