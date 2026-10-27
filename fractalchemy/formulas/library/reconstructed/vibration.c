/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        vibration.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from vibration.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz', 32: 'TC'} var_base=88

typedef struct {
    double vibration_dir;
    double vibration_angle;
    double vibration_freq;
    double vibration_amp;
    double vibration_phase;
    double vibration_dir2;
    double vibration_angle2;
    double vibration_freq2;
    double vibration_amp2;
    double vibration_phase2;
    double m_50;
    double m_58;
    double m_60;
    double m_68;
    double m_70;
    double m_78;
    double m_80;
    double m_88;
    double m_90;
    double m_98;
    double m_a0;
    double m_a8;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("vibration");
APO_VARIABLES(
    VAR_REAL_CYCLE(vibration_dir, 0.0, M_2PI, 0.0),
    VAR_REAL_CYCLE(vibration_angle, 0.0, M_2PI, M_PI_2),
    VAR_REAL(vibration_freq, 1.0),
    VAR_REAL(vibration_amp, 0.25),
    VAR_REAL_CYCLE(vibration_phase, 0.0, 1.0, 0.0),
    VAR_REAL_CYCLE(vibration_dir2, 0.0, M_2PI, M_PI_2),
    VAR_REAL_CYCLE(vibration_angle2, 0.0, M_2PI, M_PI_2),
    VAR_REAL(vibration_freq2, 1.0),
    VAR_REAL(vibration_amp2, 0.25),
    VAR_REAL_CYCLE(vibration_phase2, 0.0, 1.0, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    double t1 = VAR(vibration_angle) + VAR(vibration_dir);
    double t2 = VAR(vibration_angle2) + VAR(vibration_dir2);
    VAR(m_50) = cos(VAR(vibration_dir));
    VAR(m_58) = sin(VAR(vibration_dir));
    VAR(m_60) = cos(t1);
    VAR(m_68) = sin(t1);
    VAR(m_70) = M_2PI * VAR(vibration_freq);
    VAR(m_78) = M_2PI * VAR(vibration_phase) / VAR(vibration_freq);
    VAR(m_80) = cos(VAR(vibration_dir2));
    VAR(m_88) = sin(VAR(vibration_dir2));
    VAR(m_90) = cos(t2);
    VAR(m_98) = sin(t2);
    VAR(m_a0) = M_2PI * VAR(vibration_freq2);
    VAR(m_a8) = M_2PI * VAR(vibration_phase2) / VAR(vibration_freq2);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = sin((FTx * VAR(m_80) + FTy * VAR(m_88)) * VAR(m_a0) + VAR(m_a8)) * VAR(vibration_amp2);
    double t2 = sin((VAR(m_50) * FTx + VAR(m_58) * FTy) * VAR(m_70) + VAR(m_78)) * VAR(vibration_amp);
    FPx = (t1 * VAR(m_90) + (VAR(m_60) * t2 + FTx)) * VVAR + FPx;
    FPy = (VAR(m_98) * t1 + (t2 * VAR(m_68) + FTy)) * VVAR + FPy;
    return TRUE;
}