/*
    Fractalchemy formula library — pre_xfalloff2
    Ported by hand from the pre_xfalloff2 plugin (apophysis-plugins/plugins/pre_xfalloff2, Georg Kiehne
    "Xyrus02", GPL v2+): falloff2 with a rotated distance field. The double3/double4 structs of the
    original are written out as scalars, which is all that changed. Mode: pre (rewrites the input point).
*/

typedef struct {
    double pre_xfalloff2_scatter;
    double pre_xfalloff2_mindist;
    double pre_xfalloff2_mul_x;
    double pre_xfalloff2_mul_y;
    double pre_xfalloff2_mul_z;
    double pre_xfalloff2_mul_c;
    double pre_xfalloff2_x0;
    double pre_xfalloff2_y0;
    double pre_xfalloff2_z0;
    double pre_xfalloff2_angle;
    int pre_xfalloff2_invert;
    int pre_xfalloff2_type;
    double r_max, d_0, ca, sa;
} Variables;

#include "apoplugin.h"

#define random_double (random01() - 0.5)
#define mind(x, x0) ((x) < (x0) ? (x0) : (x))
#define scatter_adjust 0.04

APO_PLUGIN("pre_xfalloff2");
APO_VARIABLES(
    VAR_REAL_RANGE(pre_xfalloff2_scatter, EPS, DBL_MAX, 1.0),
    VAR_REAL_RANGE(pre_xfalloff2_mindist, 0.0, DBL_MAX, 0.5),
    VAR_REAL_RANGE(pre_xfalloff2_mul_x, 0.0, 1.0, 1.0),
    VAR_REAL_RANGE(pre_xfalloff2_mul_y, 0.0, 1.0, 1.0),
    VAR_REAL_RANGE(pre_xfalloff2_mul_z, 0.0, 1.0, 0.0),
    VAR_REAL_RANGE(pre_xfalloff2_mul_c, 0.0, 1.0, 0.0),
    VAR_REAL(pre_xfalloff2_x0, 0.0),
    VAR_REAL(pre_xfalloff2_y0, 0.0),
    VAR_REAL(pre_xfalloff2_z0, 0.0),
    VAR_REAL(pre_xfalloff2_angle, 0.0),
    VAR_INTEGER_RANGE(pre_xfalloff2_invert, 0, 1, 0),
    VAR_INTEGER_RANGE(pre_xfalloff2_type, 0, 2, 0)
);

int PluginVarPrepare(Variation* vp)
{
    double sa, ca;
    VAR(r_max) = scatter_adjust * VAR(pre_xfalloff2_scatter);
    VAR(d_0) = VAR(pre_xfalloff2_mindist);
    fsincos(VAR(pre_xfalloff2_angle), &sa, &ca);
    VAR(ca) = ca;
    VAR(sa) = sa;
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    const double in_x = FTx, in_y = FTy, in_z = FTz, in_c = TC;
    const double cx = VAR(pre_xfalloff2_x0), cy = VAR(pre_xfalloff2_y0), cz = VAR(pre_xfalloff2_z0);
    const double mul_x = VAR(pre_xfalloff2_mul_x), mul_y = VAR(pre_xfalloff2_mul_y), mul_z = VAR(pre_xfalloff2_mul_z), mul_c = VAR(pre_xfalloff2_mul_c);
    const double ca = VAR(ca), sa = VAR(sa);

    // the input rotated about the centre: where the distance is measured
    const double dc_x = (in_x - cx) * ca - (in_y - cy) * sa + cx;
    const double dc_y = (in_x - cx) * sa + (in_y - cy) * ca + cy;
    const double dc_z = in_z;

    const double rnd_x = random_double, rnd_y = random_double, rnd_z = random_double, rnd_c = random_double;
    const double dist_a = sqrt(sqr(dc_x - cx) + sqr(dc_y - cy) + sqr(dc_z - cz));
    const double dist_b = VAR(pre_xfalloff2_invert) != 0 ? mind(1 - dist_a, 0) : mind(dist_a, 0);
    const double dist = mind((dist_b - VAR(d_0)) * VAR(r_max), 0);

    double out_x = in_x, out_y = in_y, out_z = in_z, out_c = in_c;
    if (VAR(pre_xfalloff2_type) == 1) {
        // radial
        if (!(in_x == 0 && in_y == 0 && in_z == 0)) {
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
    } else if (VAR(pre_xfalloff2_type) == 2) {
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
        // linear, along the rotated axes: transform((1, 1), angle) about the origin
        const double tx = ca - sa, ty = sa + ca;
        out_x = in_x + mul_x * rnd_x * dist * tx;
        out_y = in_y + mul_y * rnd_y * dist * ty;
        out_z = in_z + mul_z * rnd_z * dist;
        out_c = in_c + mul_c * rnd_c * dist;
    }

    FTx = out_x * VVAR;
    FTy = out_y * VVAR;
    FTz = out_z * VVAR;
    TC = fabs(fmod(out_c, 1.0));
    return TRUE;
}
