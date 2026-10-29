/*
    Fractalchemy formula library — translated from the JWildfire variation
        MobiqNFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double mobiqN_qat;
    double mobiqN_qax;
    double mobiqN_qay;
    double mobiqN_qaz;
    double mobiqN_qbt;
    double mobiqN_qbx;
    double mobiqN_qby;
    double mobiqN_qbz;
    double mobiqN_qct;
    double mobiqN_qcx;
    double mobiqN_qcy;
    double mobiqN_qcz;
    double mobiqN_qdt;
    double mobiqN_qdx;
    double mobiqN_qdy;
    double mobiqN_qdz;
    double mobiqN_power;
    double mobiqN_dist;
    int mobiqN_colorMode;
    int mobiqN_iterations;
    int mobiqN_spaceType;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("mobiqN");

APO_VARIABLES(
    VAR_REAL(mobiqN_qat, 1),
    VAR_REAL(mobiqN_qax, 0),
    VAR_REAL(mobiqN_qay, 0),
    VAR_REAL(mobiqN_qaz, 0),
    VAR_REAL(mobiqN_qbt, 0),
    VAR_REAL(mobiqN_qbx, 0),
    VAR_REAL(mobiqN_qby, 0),
    VAR_REAL(mobiqN_qbz, 0),
    VAR_REAL(mobiqN_qct, 0),
    VAR_REAL(mobiqN_qcx, 0),
    VAR_REAL(mobiqN_qcy, 0),
    VAR_REAL(mobiqN_qcz, 1),
    VAR_REAL(mobiqN_qdt, 1),
    VAR_REAL(mobiqN_qdx, 0),
    VAR_REAL(mobiqN_qdy, 0),
    VAR_REAL(mobiqN_qdz, 0),
    VAR_REAL(mobiqN_power, 2),
    VAR_REAL(mobiqN_dist, 1),
    VAR_INTEGER(mobiqN_colorMode, 0),
    VAR_INTEGER(mobiqN_iterations, 1),
    VAR_INTEGER(mobiqN_spaceType, 0)
);

double sinh(double x)
{
    return(exp(x) - exp(- x)) * 0.5;
}

double asinh(double x)
{
    return log(x + sqrt(x * x + 1.0));
}

int PluginVarPrepare(Variation* vp)
{
    if(fabs(VAR(mobiqN_power)) < 1.0) {
        VAR(mobiqN_power) = 1.0;
    }
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double z_scale = (VAR(mobiqN_power) != 0.0) ? (4.0 * VAR(mobiqN_dist) / VAR(mobiqN_power)) : 0.0;
    double rho = sqrt(sqr(FTx) + sqr(FTy) + sqr(FTz));
    double theta = atan2(FTy, FTx);
    double phi = (rho == 0.0) ? 0.0 : acos(FTz / rho);
    double new_rho = pow(rho, z_scale);
    double new_theta = theta * VAR(mobiqN_power);
    double new_phi = phi * VAR(mobiqN_power);
    double sin_phi = sin(new_phi);
    double x_prime = new_rho * sin_phi * cos(new_theta);
    double y_prime = new_rho * sin_phi * sin(new_theta);
    double z_prime = new_rho * cos(new_phi);
    double x_mapped = x_prime, y_mapped = y_prime, z_mapped = z_prime;
    switch(VAR(mobiqN_spaceType)) {
        case 1 : x_mapped = sinh(x_prime);
        y_mapped = sinh(y_prime);
        z_mapped = sinh(z_prime);
        break;
        case 2 : x_mapped = sin(x_prime);
        y_mapped = sin(y_prime);
        z_mapped = sin(z_prime);
        break;
    }
    double x_res = x_mapped, y_res = y_mapped, z_res = z_mapped;
    double t_res_quat = 0.0, denom_sqr = 0.0;
    int iter = max(1, VAR(mobiqN_iterations));
    for(int i = 0;
    i < iter;
    i++) {
        double t2 = x_res, x2 = y_res, y2 = z_res;
        double nt_num = VAR(mobiqN_qat) * t2 - VAR(mobiqN_qax) * x2 - VAR(mobiqN_qay) * y2 + VAR(mobiqN_qbt);
        double nx_num = VAR(mobiqN_qat) * x2 + VAR(mobiqN_qax) * t2 - VAR(mobiqN_qaz) * y2 + VAR(mobiqN_qbx);
        double ny_num = VAR(mobiqN_qat) * y2 + VAR(mobiqN_qay) * t2 + VAR(mobiqN_qaz) * x2 + VAR(mobiqN_qby);
        double nz_num = VAR(mobiqN_qaz) * t2 + VAR(mobiqN_qax) * y2 - VAR(mobiqN_qay) * x2 + VAR(mobiqN_qbz);
        double dt_den = VAR(mobiqN_qct) * t2 - VAR(mobiqN_qcx) * x2 - VAR(mobiqN_qcy) * y2 + VAR(mobiqN_qdt);
        double dx_den = VAR(mobiqN_qct) * x2 + VAR(mobiqN_qcx) * t2 - VAR(mobiqN_qcz) * y2 + VAR(mobiqN_qdx);
        double dy_den = VAR(mobiqN_qct) * y2 + VAR(mobiqN_qcy) * t2 + VAR(mobiqN_qcz) * x2 + VAR(mobiqN_qdy);
        double dz_den = VAR(mobiqN_qcz) * t2 + VAR(mobiqN_qcx) * y2 - VAR(mobiqN_qcy) * x2 + VAR(mobiqN_qdz);
        denom_sqr = sqr(dt_den) + sqr(dx_den) + sqr(dy_den) + sqr(dz_den);
        if(denom_sqr != 0.0) {
            double inv_denom = 1.0 / denom_sqr;
            t_res_quat = (nt_num * dt_den + nx_num * dx_den + ny_num * dy_den + nz_num * dz_den) * inv_denom;
            x_res = (nx_num * dt_den - nt_num * dx_den - ny_num * dz_den + nz_num * dy_den) * inv_denom;
            y_res = (ny_num * dt_den - nt_num * dy_den - nz_num * dx_den + nx_num * dz_den) * inv_denom;
            z_res = (nz_num * dt_den - nx_num * dy_den + ny_num * dx_den - nt_num * dz_den) * inv_denom;
        } else {
            t_res_quat = x_res = y_res = z_res = 0.0;
        }
    }
    double x_unmapped = x_res, y_unmapped = y_res, z_unmapped = z_res;
    switch(VAR(mobiqN_spaceType)) {
        case 1 : x_unmapped = asinh(x_res);
        y_unmapped = asinh(y_res);
        z_unmapped = asinh(z_res);
        break;
        case 2 : x_unmapped = asin(x_res);
        y_unmapped = asin(y_res);
        z_unmapped = asin(z_res);
        break;
    }
    double z_inv_scale = (z_scale != 0.0) ? (1.0 / z_scale) : 0.0;
    double rho_res = sqrt(sqr(x_unmapped) + sqr(y_unmapped) + sqr(z_unmapped));
    double theta_res = atan2(y_unmapped, x_unmapped);
    double phi_res = (rho_res == 0.0) ? 0.0 : acos(z_unmapped / rho_res);
    double final_rho = pow(rho_res, z_inv_scale);
    double floored_power = floor(VAR(mobiqN_power));
    double n_theta = floor(VAR(mobiqN_power) * random01());
    double n_phi = floor(VAR(mobiqN_power) * random01());
    double final_theta = (floored_power != 0.0) ? (theta_res + n_theta * (2.0 * M_PI)) / floored_power : theta_res;
    double final_phi = (floored_power != 0.0) ? (phi_res + n_phi * (2.0 * M_PI)) / floored_power : phi_res;
    double final_sin_phi = sin(final_phi);
    double final_x = final_rho * final_sin_phi * cos(final_theta);
    double final_y = final_rho * final_sin_phi * sin(final_theta);
    double final_z = final_rho * cos(final_phi);
    switch(VAR(mobiqN_colorMode)) {
        case 1 : TC = new_rho * z_inv_scale * 0.1;
        break;
        case 2 : TC = (t_res_quat + 1.0) * 0.5;
        break;
        case 3 : TC = atan(sqrt(denom_sqr)) / (M_PI * 0.5);
        break;
        case 4 : double len = sqrt(sqr(final_x) + sqr(final_y) + sqr(final_z));
        TC = (len > 1.0e-8) ? ((final_z / len + 1.0) * 0.5) : 0.5;
        break;
        case 5 : if(rho > 1.0e-8) {
            double ratio = final_rho / rho;
            TC = atan(ratio) / (M_PI * 0.5);
        } else {
            TC = 0.5;
        }
        break;
        case 6 : double twist = final_theta - theta;
        double normalized_twist = twist / (2.0 * M_PI);
        TC = normalized_twist - floor(normalized_twist);
        break;
    }
    FPx += VVAR * final_x;
    FPy += VVAR * final_y;
    FPz += VVAR * final_z;
    return TRUE;
}
