/*
    Fractalchemy formula library — translated from the JWildfire variation
        QuasicrystalFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double quasicrystal_freq;
    double quasicrystal_amp;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("quasicrystal");

APO_VARIABLES(
    VAR_REAL(quasicrystal_freq, 3),
    VAR_REAL(quasicrystal_amp, 0.3)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double qc_sum_x = 0.0;
    double qc_sum_y = 0.0;
    double qc_step = 1.2566370614359172;
    for(int qc_k = 0;
    qc_k < 5;
    qc_k++) {
        double qc_angle = (double) qc_k * qc_step;
        double qc_proj = FTx * cos(qc_angle) + FTy * sin(qc_angle);
        double qc_wave = cos(VAR(quasicrystal_freq) * qc_proj);
        qc_sum_x += qc_wave * cos(qc_angle);
        qc_sum_y += qc_wave * sin(qc_angle);
    }
    FPx += VVAR * (FTx + VAR(quasicrystal_amp) * qc_sum_x * 0.2);
    FPy += VVAR * (FTy + VAR(quasicrystal_amp) * qc_sum_y * 0.2);
    
    return TRUE;
}
