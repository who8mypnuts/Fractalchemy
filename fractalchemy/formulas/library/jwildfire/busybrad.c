/*
    Fractalchemy formula library — translated from the JWildfire variation
        BusyBradFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    int busybrad_mode;
    double busybrad_gridSize;
    double busybrad_xOffset;
    double busybrad_yOffset;
    double busybrad_spin;
    double busybrad_twist;
    double busybrad_space;
    int busybrad_n;
    int busybrad_corner;
    double busybrad_mod_spin_strength;
    double busybrad_mod_twist_strength;
    int busybrad_sensen_post_effect;
    double busybrad_sensen_fold;
    double busybrad_vertex;
    double busybrad_sin_vertex;
    double busybrad_pie_slice;
    double busybrad_half_slice;
    double busybrad_corner_rotation;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("busybrad");

APO_VARIABLES(
    VAR_INTEGER(busybrad_mode, 2),
    VAR_REAL(busybrad_gridSize, 1),
    VAR_REAL(busybrad_xOffset, 0),
    VAR_REAL(busybrad_yOffset, 0),
    VAR_REAL(busybrad_spin, 0.1),
    VAR_REAL(busybrad_twist, 0.2),
    VAR_REAL(busybrad_space, 0.4),
    VAR_INTEGER(busybrad_n, 4),
    VAR_INTEGER(busybrad_corner, 1),
    VAR_REAL(busybrad_mod_spin_strength, 0),
    VAR_REAL(busybrad_mod_twist_strength, 0),
    VAR_INTEGER(busybrad_sensen_post_effect, 0),
    VAR_REAL(busybrad_sensen_fold, 1)
);

int PluginVarPrepare(Variation* vp)
{
    if(VAR(busybrad_mode) == 1 || VAR(busybrad_mode) == 2) {
        if(VAR(busybrad_n) < 2) VAR(busybrad_n) = 2;
        VAR(busybrad_vertex) = M_PI * (VAR(busybrad_n) - 2) / (2.0 * VAR(busybrad_n));
        VAR(busybrad_sin_vertex) = sin(VAR(busybrad_vertex));
        VAR(busybrad_pie_slice) = (2.0 * M_PI) / VAR(busybrad_n);
        VAR(busybrad_half_slice) = VAR(busybrad_pie_slice) / 2.0;
        VAR(busybrad_corner_rotation) = (VAR(busybrad_corner) - 1.0) * VAR(busybrad_pie_slice);
    }
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double cellCenterX = (VAR(busybrad_gridSize) == 0.0) ? 0.0 : VAR(busybrad_gridSize) * round(FTx / VAR(busybrad_gridSize));
    double cellCenterY = (VAR(busybrad_gridSize) == 0.0) ? 0.0 : VAR(busybrad_gridSize) * round(FTy / VAR(busybrad_gridSize));
    double x = FTx - cellCenterX;
    double y = FTy - cellCenterY;
    double local_x = x - VAR(busybrad_xOffset);
    double local_y = y + VAR(busybrad_yOffset);
    double transformedX = 0, transformedY = 0;
    if(VAR(busybrad_mode) == 0) {
        double rr = sqrt(local_x * local_x + local_y * local_y);
        if(rr < VVAR) {
            double a = atan2(local_y, local_x) + VAR(busybrad_spin) + VAR(busybrad_twist) * (VVAR - rr);
            double r2 = VVAR * rr;
            transformedX = r2 * cos(a);
            transformedY = r2 * sin(a);
        } else {
            double r2 = (rr != 0) ? VVAR * (1.0 + VAR(busybrad_space) / rr) : 0;
            transformedX = r2 * local_x;
            transformedY = r2 * local_y;
        }
    } else if(VAR(busybrad_mode) == 1) {
        double modulus = sqrt(local_x * local_x + local_y * local_y);
        double n_d = (double)(VAR(busybrad_n) == 0 ? 1 : VAR(busybrad_n));
        double theta_check = atan2(local_y, local_x);
        double r_poly = VVAR * cos(M_PI / n_d) / cos(theta_check - (2.0 * M_PI) / n_d * floor(n_d * theta_check / (2.0 * M_PI) + 0.5));
        if(modulus < r_poly) {
            double twist_effect = (r_poly > 1e-9) ? VAR(busybrad_twist) * (r_poly - modulus) / r_poly : 0.0;
            double theta = atan2(local_y, local_x) + VAR(busybrad_spin) + twist_effect;
            transformedX = modulus * cos(theta);
            transformedY = modulus * sin(theta);
        } else {
            double new_modulus = (modulus != 0) ? VVAR * (1.0 + VAR(busybrad_space) / modulus) : 0;
            transformedX = new_modulus * local_x;
            transformedY = new_modulus * local_y;
        }
    } else {
        double rr = sqrt(local_x * local_x + local_y * local_y);
        double modulation_value = (rr != 0) ? VVAR * (1.0 + VAR(busybrad_space) / rr) : 0;
        double dynamic_spin = VAR(busybrad_spin) + (modulation_value * VAR(busybrad_mod_spin_strength));
        double dynamic_twist = VAR(busybrad_twist) + (modulation_value * VAR(busybrad_mod_twist_strength));
        double modulus = rr;
        double n_d = (double)(VAR(busybrad_n) == 0 ? 1 : VAR(busybrad_n));
        double theta_check = atan2(local_y, local_x);
        double r_poly = VVAR * cos(M_PI / n_d) / cos(theta_check - (2.0 * M_PI) / n_d * floor(n_d * theta_check / (2.0 * M_PI) + 0.5));
        if(modulus < r_poly) {
            double twist_effect = (r_poly > 1e-9) ? dynamic_twist * (r_poly - modulus) / r_poly : 0.0;
            double theta = atan2(local_y, local_x) + dynamic_spin + twist_effect;
            transformedX = modulus * cos(theta);
            transformedY = modulus * sin(theta);
        } else {
            transformedX = modulation_value * local_x;
            transformedY = modulation_value * local_y;
        }
    }
    if(VAR(busybrad_sensen_post_effect) == 1 && VAR(busybrad_sensen_fold) != 0.0) {
        double nr_x = floor(transformedX * VAR(busybrad_sensen_fold));
        if((nr_x >= 0 && nr_x % 2 == 1) || (nr_x < 0 && nr_x % 2 == 0)) {
            transformedX = - transformedX;
        }
        double nr_y = floor(transformedY * VAR(busybrad_sensen_fold));
        if((nr_y >= 0 && nr_y % 2 == 1) || (nr_y < 0 && nr_y % 2 == 0)) {
            transformedY = - transformedY;
        }
    }
    FPx += cellCenterX + transformedX - VAR(busybrad_xOffset);
    FPy += cellCenterY + transformedY + VAR(busybrad_yOffset);
    
    return TRUE;
}
