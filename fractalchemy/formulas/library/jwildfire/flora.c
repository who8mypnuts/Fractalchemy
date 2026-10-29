/*
    Fractalchemy formula library — translated from the JWildfire variation
        FloraFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    int flora_leafType;
    double flora_filled;
    double flora_scale;
    double flora_distort;
    double flora_shapeMod;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("flora");

APO_VARIABLES(
    VAR_INTEGER(flora_leafType, 0),
    VAR_REAL(flora_filled, 1),
    VAR_REAL(flora_scale, 1),
    VAR_REAL(flora_distort, 0.1),
    VAR_REAL(flora_shapeMod, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t = atan2(FTy, FTx);
    double r = (VAR(flora_filled) > 0 && VAR(flora_filled) > random01()) ? VVAR * random01() : VVAR;
    double lx = 0, ly = 0;
    switch(VAR(flora_leafType)) {
        case 0 : t += M_PI_2;
        double ginkgo_r = 0;
        if(sin(t) > 0) {
            ginkgo_r = 1.0;
            ginkgo_r -= (VAR(flora_shapeMod) * 0.8) * pow(cos(t), 50.0);
            ginkgo_r *= (1.0 + 0.05 * cos(8.0 * t));
        }
        lx = ginkgo_r * cos(t);
        ly = ginkgo_r * sin(t);
        break;
        case 1 : t += M_PI_2;
        double cannabis_r = (1.0 + (0.5 + VAR(flora_shapeMod) * 0.8) * cos(8 * t)) * (1.0 + 0.1 * cos(24 * t)) * (0.9 + 0.05 * cos(200 * t)) * (1 + sin(t));
        lx = cannabis_r * sin(t);
        ly = - cannabis_r * cos(t);
        break;
        case 2 : double effectiveCloverMod = - 6.0 * VAR(flora_shapeMod) + 0.5;
        double cleftTerm = 0.5 + effectiveCloverMod * 0.5;
        t += M_PI / 4.0;
        double clover_r = (1 + 0.8 * cos(4.0 * t)) * (1 - cleftTerm * pow(sin(4.0 * t), 2.0));
        lx = clover_r * cos(t);
        ly = clover_r * sin(t);
        break;
        case 3 : t += M_PI_2;
        double rose_r = sin(t);
        if(rose_r < 0) rose_r = 0;
        rose_r *= (1.0 + (VAR(flora_shapeMod) * 0.1) * cos(40.0 * t));
        lx = rose_r * cos(t) * 0.7;
        ly = rose_r * sin(t);
        break;
        case 4 : t += M_PI_2;
        double daisy_r = 0.6 * (1.2 + cos((8.0 + VAR(flora_shapeMod) * 16.0) * t));
        lx = daisy_r * cos(t);
        ly = daisy_r * sin(t);
        break;
        case 5 : t += M_PI_2;
        double butterfly_r = exp(cos(t)) - 2.0 * cos(4.0 * t) + pow(sin(t / 12.0), 5.0);
        butterfly_r *= (0.7 + VAR(flora_shapeMod) * 0.6);
        lx = butterfly_r * sin(t);
        ly = - butterfly_r * cos(t);
        break;
        case 6 : t += M_PI_2;
        double oak_r = (1.0 + 0.8 * sin(t)) * (1.0 + (0.1 + VAR(flora_shapeMod) * 0.2) * cos(14.0 * t));
        lx = oak_r * sin(t);
        ly = - oak_r * cos(t);
        break;
        case 7 : t += M_PI_2;
        double teardrop_r = (1.0 - 0.9 * sin(t));
        teardrop_r *= (1.0 + 0.02 * cos(60.0 * t));
        lx = teardrop_r * cos(t) * (0.6 + VAR(flora_shapeMod) * 0.4);
        ly = teardrop_r * sin(t);
        break;
        case 8 : double lotus_r = 1.0 + 0.05 * cos(12 * t);
        double center_offset = 0.1 + VAR(flora_shapeMod) * 0.4;
        lx = lotus_r * cos(t);
        ly = lotus_r * sin(t) + (center_offset * (1 - lotus_r));
        break;
        case 9 : t += M_PI_2;
        double sycamore_r = (1.0 - 0.5 * sin(t));
        sycamore_r *= (1.0 + (0.1 + VAR(flora_shapeMod) * 0.4) * cos(5.0 * t));
        sycamore_r *= (1.0 + 0.05 * cos(25.0 * t));
        lx = sycamore_r * sin(t);
        ly = - sycamore_r * cos(t);
        break;
        case 10 : t += M_PI_2;
        double ash_r = sin(t) > 0 ? sin(t) * (1.0 + (0.05 + VAR(flora_shapeMod) * 0.3) * cos(30.0 * t)) : 0;
        lx = ash_r * cos(t) * 0.6;
        ly = ash_r * sin(t);
        break;
        case 11 : t += M_PI_2;
        double monstera_base_r = 1.0 - 0.9 * sin(t);
        if(monstera_base_r < 0) monstera_base_r = 0;
        double fenestrations = 1.0 - (VAR(flora_shapeMod) * 0.8) * pow(sin(t * 2.5), 10.0);
        fenestrations *= 1.0 - (VAR(flora_shapeMod) * 0.7) * pow(cos(t * 3.5), 10.0);
        double monstera_r = monstera_base_r * fenestrations;
        lx = monstera_r * cos(t);
        ly = monstera_r * sin(t);
        break;
        case 12 : t += M_PI_2;
        double anise_r = 1.0 + (0.2 + VAR(flora_shapeMod) * 0.4) * cos(8.0 * t);
        lx = anise_r * cos(t);
        ly = anise_r * sin(t);
        break;
        case 13 : t += M_PI_2;
        double holly_base_r = 1.0;
        double num_points = 10.0;
        double spike_depth = 0.15 + VAR(flora_shapeMod) * 0.2;
        double spikes = 1.0 - spike_depth * fabs(sin(t * num_points / 2.0));
        double holly_r = holly_base_r * spikes;
        lx = holly_r * cos(t) * 0.7;
        ly = holly_r * sin(t);
        break;
        case 14 : t += M_PI_2;
        double sweetgum_base_r = 1.0;
        double sweetgum_num_points = 5.0;
        double sweetgum_point_depth = 0.3 + VAR(flora_shapeMod) * 0.4;
        double sweetgum_sharp_valleys = 1.0 - sweetgum_point_depth * fabs(sin(t * sweetgum_num_points / 2.0));
        double sweetgum_serrations = 1.0 + 0.04 * cos(40 * t);
        double sweetgum_r = sweetgum_base_r * sweetgum_sharp_valleys * sweetgum_serrations;
        lx = sweetgum_r * cos(t);
        ly = sweetgum_r * sin(t);
        break;
        case 15 : t += M_PI_2;
        double lobe_depth = 0.1 + VAR(flora_shapeMod) * 0.2;
        double base_shape = 1.0 + lobe_depth * cos(3.0 * t) - (lobe_depth * 0.5) * cos(5.0 * t);
        double serrations = 1.0 + 0.03 * cos(20.0 * t) + 0.02 * cos(35.0 * t);
        double grape_r = base_shape * serrations;
        lx = grape_r * cos(t);
        ly = grape_r * sin(t);
        break;
        case 16 : t += M_PI_2;
        double castor_lobe_depth = 0.3 + VAR(flora_shapeMod) * 0.5;
        double castor_base_shape = 1.0 + castor_lobe_depth * cos(7.0 * t);
        double castor_serration_depth = 0.05;
        double castor_serrations = 1.0 + castor_serration_depth * cos(42.0 * t);
        double castor_r = castor_base_shape * castor_serrations;
        lx = castor_r * cos(t);
        ly = castor_r * sin(t);
        break;
        case 17 : t += M_PI_2;
        double hosta_base_r = (1.0 - 0.9 * sin(t));
        double waviness = 0.02 + VAR(flora_shapeMod) * 0.05;
        double hosta_r = hosta_base_r * (1.0 + waviness * sin(10.0 * t));
        lx = hosta_r * cos(t) * 1.2;
        ly = hosta_r * sin(t);
        break;
        case 18 : t = atan2(FTy, FTx);
        double alocasia_base_r = 1.0 - sin(t);
        double alocasia_lobe_definition = 1.0 - (0.1 + VAR(flora_shapeMod) * 0.4) * pow(cos(t), 2.0);
        double alocasia_r = alocasia_base_r * alocasia_lobe_definition;
        alocasia_r *= (1.0 + 0.03 * sin(15.0 * t));
        lx = alocasia_r * cos(t) * 0.7;
        ly = alocasia_r * sin(t);
        break;
        case 19 : t += M_PI_2;
        double dandelion_r = 0.8 * (1.1 + cos((20.0 + VAR(flora_shapeMod) * 40.0) * t) * 0.3);
        lx = dandelion_r * cos(t);
        ly = dandelion_r * sin(t);
        break;
        case 20 : t += M_PI_2;
        double columbine_r = 1.0 + sin(t) + (0.2 + VAR(flora_shapeMod) * 0.6) * sin(5.0 * t - M_PI_2);
        lx = columbine_r * cos(t);
        ly = columbine_r * sin(t);
        break;
        case 21 : t = atan2(FTy, FTx);
        double birch_base_r = 1.0 - 0.9 * sin(t);
        double primary_serrations = 1.0 + 0.05 * cos(20.0 * t);
        double secondary_serrations = 1.0 + (0.02 + VAR(flora_shapeMod) * 0.03) * cos(40.0 * t);
        double birch_r = birch_base_r * primary_serrations * secondary_serrations;
        lx = birch_r * cos(t) * 0.8;
        ly = birch_r * sin(t);
        break;
        case 22 : t += M_PI_2;
        double tulip_r = pow(fabs(cos(t)), 0.3) + pow(fabs(sin(t)), 2.0 + VAR(flora_shapeMod) * 2.0);
        lx = tulip_r * sin(t);
        ly = - tulip_r * cos(t) * 0.6;
        break;
        case 23 : t += M_PI_2;
        double linden_r = 1.0 - 0.9 * sin(t + (VAR(flora_shapeMod) - 0.5) * 0.2);
        lx = linden_r * sin(t) * 1.1;
        ly = - linden_r * cos(t);
        break;
        case 24 : t = atan2(FTy, FTx) * (2.0 + VAR(flora_shapeMod) * 4.0) * M_PI;
        double fiddlehead_r = 0.05 * t;
        lx = fiddlehead_r * cos(t);
        ly = fiddlehead_r * sin(t);
        break;
    }
    if(VAR(flora_distort) != 0) {
        double origX = FTx;
        double origY = FTy;
        lx += VAR(flora_distort) * sin(origY * 5.0);
        ly += VAR(flora_distort) * cos(origX * 5.0);
    }
    FPx += r * lx * VAR(flora_scale);
    FPy += r * ly * VAR(flora_scale);
    
    return TRUE;
}
