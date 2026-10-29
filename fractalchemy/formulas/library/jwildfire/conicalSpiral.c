/*
    Fractalchemy formula library — translated from the JWildfire variation
        ConicalSpiralFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double conicalSpiral_turns;
    double conicalSpiral_radius;
    double conicalSpiral_height;
    int conicalSpiral_mode;
    double conicalSpiral_z_wave_freq;
    double conicalSpiral_z_wave_amp;
    double conicalSpiral_twist;
    double conicalSpiral_thickness;
    int conicalSpiral_solid;
    int conicalSpiral_colorize;
    int conicalSpiral_colorMode;
    double conicalSpiral_colorSpeed;
    double conicalSpiral_colorOffset;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("conicalSpiral");

APO_VARIABLES(
    VAR_REAL(conicalSpiral_turns, 8),
    VAR_REAL(conicalSpiral_radius, 1.2),
    VAR_REAL(conicalSpiral_height, 1),
    VAR_INTEGER(conicalSpiral_mode, 0),
    VAR_REAL(conicalSpiral_z_wave_freq, 0),
    VAR_REAL(conicalSpiral_z_wave_amp, 0),
    VAR_REAL(conicalSpiral_twist, 0),
    VAR_REAL(conicalSpiral_thickness, 0),
    VAR_INTEGER(conicalSpiral_solid, 0),
    VAR_INTEGER(conicalSpiral_colorize, 0),
    VAR_INTEGER(conicalSpiral_colorMode, 0),
    VAR_REAL(conicalSpiral_colorSpeed, 1),
    VAR_REAL(conicalSpiral_colorOffset, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t;
    if(VAR(conicalSpiral_mode) == 1) {
        t = fmod(fabs(FTy), 1.0);
    } else if(VAR(conicalSpiral_mode) == 2) {
        t = fmod(fabs(FTz), 1.0);
    } else {
        t = fmod(fabs(FTx), 1.0);
    }
    double angle = t * (2.0 * M_PI) * VAR(conicalSpiral_turns);
    double currentRadius = t * VAR(conicalSpiral_radius);
    double z = t * VAR(conicalSpiral_height);
    if(VAR(conicalSpiral_z_wave_amp) != 0.0) {
        z += sin(t * (2.0 * M_PI) * VAR(conicalSpiral_z_wave_freq)) * VAR(conicalSpiral_z_wave_amp);
    }
    double final_angle = angle;
    if(VAR(conicalSpiral_twist) != 0.0) {
        final_angle += z * VAR(conicalSpiral_twist);
    }
    double x = currentRadius * cos(final_angle);
    double y = currentRadius * sin(final_angle);
    if(VAR(conicalSpiral_thickness) > 0.0) {
        if(VAR(conicalSpiral_solid) > 0) {
            x += random01() * VAR(conicalSpiral_thickness);
            y += random01() * VAR(conicalSpiral_thickness);
            z += random01() * VAR(conicalSpiral_thickness);
        } else {
            x += FTx * VAR(conicalSpiral_thickness);
            y += FTy * VAR(conicalSpiral_thickness);
            z += FTz * VAR(conicalSpiral_thickness);
        }
    }
    FPx += x * VVAR;
    FPy += y * VVAR;
    FPz += z * VVAR;
    if(VAR(conicalSpiral_colorize) > 0) {
        double colorDriver = 0.0;
        switch(VAR(conicalSpiral_colorMode)) {
            case 0 : colorDriver = t;
            break;
            case 1 : colorDriver = currentRadius;
            break;
            case 2 : colorDriver = fmod(angle, (2.0 * M_PI)) / (2.0 * M_PI);
            break;
            case 3 : default : colorDriver = z;
            break;
        }
        TC = fmod(fabs(colorDriver * VAR(conicalSpiral_colorSpeed) + VAR(conicalSpiral_colorOffset)), 1.0);
    }
    return TRUE;
}
