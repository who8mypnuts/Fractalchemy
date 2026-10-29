/*
    Fractalchemy formula library — translated from the JWildfire variation
        WavesPhaseFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double waves_phase_scale_x;
    double waves_phase_scale_y;
    double waves_phase_freq_x;
    double waves_phase_freq_y;
    double waves_phase_phase_x;
    double waves_phase_phase_y;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("waves_phase");

APO_VARIABLES(
    VAR_REAL(waves_phase_scale_x, 0.25),
    VAR_REAL(waves_phase_scale_y, 0.25),
    VAR_REAL(waves_phase_freq_x, 2),
    VAR_REAL(waves_phase_freq_y, 2),
    VAR_REAL(waves_phase_phase_x, 0),
    VAR_REAL(waves_phase_phase_y, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double safe_sx2 = (fabs(VAR(waves_phase_scale_x)) < 1e-4) ? ((VAR(waves_phase_scale_x) + 1e-5 < 0.0 ? - 1.0 : 1.0) * 1e-4) : VAR(waves_phase_scale_x) * VAR(waves_phase_scale_x);
    double safe_sy2 = (fabs(VAR(waves_phase_scale_y)) < 1e-4) ? ((VAR(waves_phase_scale_y) + 1e-5 < 0.0 ? - 1.0 : 1.0) * 1e-4) : VAR(waves_phase_scale_y) * VAR(waves_phase_scale_y);
    FPx += VVAR * (FTx + VAR(waves_phase_scale_x) * sin(FTy * VAR(waves_phase_freq_x) / safe_sx2 + VAR(waves_phase_phase_x)));
    FPy += VVAR * (FTy + VAR(waves_phase_scale_y) * sin(FTx * VAR(waves_phase_freq_y) / safe_sy2 + VAR(waves_phase_phase_y)));
    
    return TRUE;
}
