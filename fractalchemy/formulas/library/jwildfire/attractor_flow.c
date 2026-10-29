/*
    Fractalchemy formula library — translated from the JWildfire variation
        AttractorFlowFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    int attractor_flow_preset;
    int attractor_flow_attractorMode;
    int attractor_flow_waveMode;
    int attractor_flow_zMode;
    double attractor_flow_yScale;
    double attractor_flow_xScale;
    double attractor_flow_zScale;
    double attractor_flow_xAmplitude;
    double attractor_flow_yAmplitude;
    double attractor_flow_zAmplitude;
    double attractor_flow_freqX;
    double attractor_flow_freqY;
    double attractor_flow_phaseX;
    double attractor_flow_phaseY;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("attractor_flow");

APO_VARIABLES(
    VAR_INTEGER(attractor_flow_preset, 0),
    VAR_INTEGER(attractor_flow_attractorMode, 0),
    VAR_INTEGER(attractor_flow_waveMode, 0),
    VAR_INTEGER(attractor_flow_zMode, 0),
    VAR_REAL(attractor_flow_yScale, -1.7),
    VAR_REAL(attractor_flow_xScale, 1.8),
    VAR_REAL(attractor_flow_zScale, 1.5),
    VAR_REAL(attractor_flow_xAmplitude, -0.5),
    VAR_REAL(attractor_flow_yAmplitude, -1.9),
    VAR_REAL(attractor_flow_zAmplitude, 1.2),
    VAR_REAL(attractor_flow_freqX, 1),
    VAR_REAL(attractor_flow_freqY, 1),
    VAR_REAL(attractor_flow_phaseX, 0),
    VAR_REAL(attractor_flow_phaseY, 0)
);

void applyPreset(int pValue)
{
    VAR(attractor_flow_preset) = pValue;
    switch(pValue) {
        case 1 : VAR(attractor_flow_attractorMode) = 0;
        VAR(attractor_flow_waveMode) = 0;
        VAR(attractor_flow_zMode) = 0;
        VAR(attractor_flow_yScale) = - 1.7;
        VAR(attractor_flow_xScale) = 1.8;
        VAR(attractor_flow_xAmplitude) = - 0.5;
        VAR(attractor_flow_yAmplitude) = - 1.9;
        VAR(attractor_flow_freqX) = 1.0;
        VAR(attractor_flow_freqY) = 1.0;
        VAR(attractor_flow_phaseX) = 0.0;
        VAR(attractor_flow_phaseY) = 0.0;
        break;
        case 2 : VAR(attractor_flow_attractorMode) = 1;
        VAR(attractor_flow_waveMode) = 1;
        VAR(attractor_flow_zMode) = 0;
        VAR(attractor_flow_yScale) = - 2.0;
        VAR(attractor_flow_xScale) = - 2.0;
        VAR(attractor_flow_xAmplitude) = 1.2;
        VAR(attractor_flow_yAmplitude) = - 1.9;
        break;
        case 3 : VAR(attractor_flow_attractorMode) = 2;
        VAR(attractor_flow_waveMode) = 2;
        VAR(attractor_flow_zMode) = 0;
        VAR(attractor_flow_yScale) = 1.6;
        VAR(attractor_flow_xScale) = - 1.9;
        VAR(attractor_flow_xAmplitude) = 1.2;
        VAR(attractor_flow_yAmplitude) = - 1.8;
        break;
        case 4 : VAR(attractor_flow_attractorMode) = 0;
        VAR(attractor_flow_waveMode) = 0;
        VAR(attractor_flow_zMode) = 1;
        VAR(attractor_flow_yScale) = 1.2;
        VAR(attractor_flow_xScale) = 1.2;
        VAR(attractor_flow_zScale) = 1.4;
        VAR(attractor_flow_xAmplitude) = - 1.8;
        VAR(attractor_flow_yAmplitude) = - 1.3;
        VAR(attractor_flow_zAmplitude) = 1.1;
        break;
    }
}

double selectWave(double value)
{
    switch(VAR(attractor_flow_waveMode)) {
        case 1 : return sign(sin(value));
        case 2 : return asin(sin(value)) * (2.0 / M_PI);
        case 3 : return 2.0 * (value / (2.0 * M_PI) - floor(0.5 + value / (2.0 * M_PI)));
        default : return sin(value);
    }
}

double selectCosWave(double value)
{
    return selectWave(value + M_PI_2);
}

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double x = FTx, y = FTy, z = FTz;
    double newX = 0.0, newY = 0.0, newZ = 0.0;
    switch(VAR(attractor_flow_attractorMode)) {
        case 1 : newX = selectWave(VAR(attractor_flow_yScale) * y) - selectCosWave(VAR(attractor_flow_xScale) * x);
        newY = selectWave(VAR(attractor_flow_xAmplitude) * (VAR(attractor_flow_zMode) == 1 ? z : x)) - selectCosWave(VAR(attractor_flow_yAmplitude) * y);
        break;
        case 2 : newX = VAR(attractor_flow_yAmplitude) * selectWave(VAR(attractor_flow_yScale) * x) - selectWave(VAR(attractor_flow_xScale) * y);
        newY = VAR(attractor_flow_xAmplitude) * selectCosWave(VAR(attractor_flow_yScale) * (VAR(attractor_flow_zMode) == 1 ? z : x)) + selectCosWave(VAR(attractor_flow_xScale) * y);
        break;
        case 3 : double g_x = VAR(attractor_flow_xAmplitude) * x + (2.0 * (1.0 - VAR(attractor_flow_xAmplitude)) * x * x) / (1.0 + x * x);
        newY = (VAR(attractor_flow_yScale) * y) + g_x;
        newX = - x + g_x;
        break;
        default : newX = selectWave(VAR(attractor_flow_yScale) * y * VAR(attractor_flow_freqY) + VAR(attractor_flow_phaseY)) + VAR(attractor_flow_xAmplitude) * selectCosWave(VAR(attractor_flow_yScale) * x * VAR(attractor_flow_freqX) + VAR(attractor_flow_phaseX));
        newY = selectWave(VAR(attractor_flow_xScale) * (VAR(attractor_flow_zMode) == 1 ? z : x) * VAR(attractor_flow_freqX) + VAR(attractor_flow_phaseX)) + VAR(attractor_flow_yAmplitude) * selectCosWave(VAR(attractor_flow_xScale) * y * VAR(attractor_flow_freqY) + VAR(attractor_flow_phaseY));
        break;
    }
    FPx += (newX - x) * VVAR;
    FPy += (newY - y) * VVAR;
    
    return TRUE;
}
