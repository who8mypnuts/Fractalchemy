/*
    Fractalchemy formula library — falloff3
    Ported by hand from the falloff3 plugin (apophysis-plugins/plugins/falloff3, Georg Kiehne "Xyrus02",
    GPL v2+; "partially adapted from the falloff variation of MetaCore"): the double3/double4 structs
    of the original are written out as scalars, which is all that changed.
    Mode: normal (reads the input point, adds to the accumulator)
*/

typedef struct {
    int falloff3_blur_type;
    int falloff3_blur_shape;
    double falloff3_blur_strength;
    double falloff3_min_distance;
    int falloff3_invert_distance;
    double falloff3_mul_x;
    double falloff3_mul_y;
    double falloff3_mul_z;
    double falloff3_mul_c;
    double falloff3_center_x;
    double falloff3_center_y;
    double falloff3_center_z;
    double falloff3_alpha;
    double r_max, d_0;
} Variables;

#include "apoplugin.h"

#define random_double (random01() - 0.5)
#define mind(x, x0) ((x) < (x0) ? (x0) : (x))
#define sgnd(x) ((x) < 0 ? -1 : 1)
#define scatter_adjust 0.04

inline double log_scale(const double x) { return x == 0 ? 0 : log((fabs(x) + 1.0) * M_E) * sgnd(x) / M_E; }
inline double log_map(const double x) { return x == 0 ? 0 : (M_E + log(x * M_E)) / 4.0 * sgnd(x); }

APO_PLUGIN("falloff3");
APO_VARIABLES(
    VAR_INTEGER_RANGE(falloff3_blur_type, 0, 3, 0),
    VAR_INTEGER_RANGE(falloff3_blur_shape, 0, 1, 0),
    VAR_REAL_RANGE(falloff3_blur_strength, EPS, DBL_MAX, 1.0),
    VAR_REAL_RANGE(falloff3_min_distance, 0.0, DBL_MAX, 0.5),
    VAR_INTEGER_RANGE(falloff3_invert_distance, 0, 1, 0),
    VAR_REAL_RANGE(falloff3_mul_x, 0.0, 1.0, 1.0),
    VAR_REAL_RANGE(falloff3_mul_y, 0.0, 1.0, 1.0),
    VAR_REAL_RANGE(falloff3_mul_z, 0.0, 1.0, 0.0),
    VAR_REAL_RANGE(falloff3_mul_c, 0.0, 1.0, 0.0),
    VAR_REAL(falloff3_center_x, 0.0),
    VAR_REAL(falloff3_center_y, 0.0),
    VAR_REAL(falloff3_center_z, 0.0),
    VAR_REAL(falloff3_alpha, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(r_max) = scatter_adjust * VAR(falloff3_blur_strength);
    VAR(d_0) = VAR(falloff3_min_distance);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    const double in_x = FTx, in_y = FTy, in_z = FTz, in_c = TC;
    const double mul_x = VAR(falloff3_mul_x), mul_y = VAR(falloff3_mul_y), mul_z = VAR(falloff3_mul_z), mul_c = VAR(falloff3_mul_c);
    const double rnd_x = random_double, rnd_y = random_double, rnd_z = random_double, rnd_c = random_double;
    const double r_max = VAR(r_max), alpha = VAR(falloff3_alpha);

    double radius;
    if (VAR(falloff3_blur_shape) == 1) {
        // square
        radius = mind(fabs(in_x - VAR(falloff3_center_x)), mind(fabs(in_y - VAR(falloff3_center_y)), fabs(in_z - VAR(falloff3_center_z))));
    } else {
        // circle
        radius = sqrt(sqr(in_x - VAR(falloff3_center_x)) + sqr(in_y - VAR(falloff3_center_y)) + sqr(in_z - VAR(falloff3_center_z)));
    }
    const double dist = mind(((VAR(falloff3_invert_distance) != 0 ? mind(1 - radius, 0) : mind(radius, 0)) - VAR(d_0)) * r_max, 0);

    double out_x = in_x, out_y = in_y, out_z = in_z, out_c = in_c;
    if (VAR(falloff3_blur_type) == 1) {
        // radial
        if (!(in_x == 0 && in_y == 0 && in_z == 0)) {
            const double r_in = sqrt(sqr(in_x) + sqr(in_y) + sqr(in_z));
            const double a = mul_y * dist + alpha * dist / sqrt(r_max);
            const double b = mul_z * dist;
            const double sigma = asin(in_z / r_in) + b * rnd_z;
            const double phi = atan2(in_y, in_x) + a * rnd_y;
            const double r = r_in + mul_x * rnd_x * dist;
            double sigma_s, sigma_c; fsincos(sigma, &sigma_s, &sigma_c);
            double phi_s, phi_c; fsincos(phi, &phi_s, &phi_c);
            out_x = r * sigma_c * phi_c;
            out_y = r * sigma_c * phi_s;
            out_z = r * sigma_s;
            out_c = in_c + mul_c * rnd_c * dist;
        }
    } else if (VAR(falloff3_blur_type) == 2) {
        // log
        const double coeff = r_max <= EPS ? dist : dist + alpha * (log_map(dist) - dist);
        out_x = in_x + log_map(mul_x) * log_scale(rnd_x) * coeff;
        out_y = in_y + log_map(mul_y) * log_scale(rnd_y) * coeff;
        out_z = in_z + log_map(mul_z) * log_scale(rnd_z) * coeff;
        out_c = in_c + log_map(mul_c) * log_scale(rnd_c) * coeff;
    } else if (VAR(falloff3_blur_type) == 0) {
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
    }

    FPx += out_x * VVAR;
    FPy += out_y * VVAR;
    FPz += out_z * VVAR;
    TC = fabs(fmod(out_c, 1.0));
    return TRUE;
}
