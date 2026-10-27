/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        vibration2.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from vibration2.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz', 32: 'TC'} var_base=88

typedef struct {
    double vibration2_dir;
    double vibration2_angle;
    double vibration2_freq;
    double vibration2_amp;
    double vibration2_phase;
    double vibration2_dir2;
    double vibration2_angle2;
    double vibration2_freq2;
    double vibration2_amp2;
    double vibration2_phase2;
    double vibration2_dm;
    double vibration2_dmfreq;
    double vibration2_tm;
    double vibration2_tmfreq;
    double vibration2_fm;
    double vibration2_fmfreq;
    double vibration2_am;
    double vibration2_amfreq;
    double vibration2_d2m;
    double vibration2_d2mfreq;
    double vibration2_t2m;
    double vibration2_t2mfreq;
    double vibration2_f2m;
    double vibration2_f2mfreq;
    double vibration2_a2m;
    double vibration2_a2mfreq;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("vibration2");
APO_VARIABLES(
    VAR_REAL_CYCLE(vibration2_dir, 0.0, M_2PI, 0.0),
    VAR_REAL_CYCLE(vibration2_angle, 0.0, M_2PI, M_PI_2),
    VAR_REAL(vibration2_freq, 1.0),
    VAR_REAL(vibration2_amp, 0.25),
    VAR_REAL_CYCLE(vibration2_phase, 0.0, 1.0, 0.0),
    VAR_REAL_CYCLE(vibration2_dir2, 0.0, M_2PI, M_PI_2),
    VAR_REAL_CYCLE(vibration2_angle2, 0.0, M_2PI, M_PI_2),
    VAR_REAL(vibration2_freq2, 1.0),
    VAR_REAL(vibration2_amp2, 0.25),
    VAR_REAL_CYCLE(vibration2_phase2, 0.0, 1.0, 0.0),
    VAR_REAL(vibration2_dm, 0.0),
    VAR_REAL(vibration2_dmfreq, 0.1),
    VAR_REAL(vibration2_tm, 0.0),
    VAR_REAL(vibration2_tmfreq, 0.1),
    VAR_REAL(vibration2_fm, 0.0),
    VAR_REAL(vibration2_fmfreq, 0.1),
    VAR_REAL(vibration2_am, 0.0),
    VAR_REAL(vibration2_amfreq, 0.1),
    VAR_REAL(vibration2_d2m, 0.0),
    VAR_REAL(vibration2_d2mfreq, 0.1),
    VAR_REAL(vibration2_t2m, 0.0),
    VAR_REAL(vibration2_t2mfreq, 0.1),
    VAR_REAL(vibration2_f2m, 0.0),
    VAR_REAL(vibration2_f2mfreq, 0.1),
    VAR_REAL(vibration2_a2m, 0.0),
    VAR_REAL(vibration2_a2mfreq, 0.1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = cos(VAR(vibration2_dir2)) * FTx + sin(VAR(vibration2_dir2)) * FTy;
    double t2 = cos(M_2PI * (VAR(vibration2_d2mfreq) * t1)) * VAR(vibration2_d2m) + VAR(vibration2_dir2);
    double t3 = cos(M_2PI * (t1 * VAR(vibration2_t2mfreq))) * VAR(vibration2_t2m) + VAR(vibration2_angle2) + t2;
    double t4 = sin((FTx * cos(t2) + FTy * sin(t2)) * (M_2PI * VAR(vibration2_freq2)) + (cos(M_2PI * (t1 * VAR(vibration2_f2mfreq))) * VAR(vibration2_f2m) / VAR(vibration2_freq2)) + (M_2PI * VAR(vibration2_phase2) / VAR(vibration2_freq2))) * (cos(M_2PI * (t1 * VAR(vibration2_a2mfreq))) * VAR(vibration2_a2m) * VAR(vibration2_amp2) + VAR(vibration2_amp2));
    double t5 = cos(VAR(vibration2_dir)) * FTx + sin(VAR(vibration2_dir)) * FTy;
    double t6 = cos(M_2PI * (VAR(vibration2_dmfreq) * t5)) * VAR(vibration2_dm) + VAR(vibration2_dir);
    double t7 = cos(M_2PI * (t5 * VAR(vibration2_tmfreq))) * VAR(vibration2_tm) + VAR(vibration2_angle) + t6;
    double t8 = sin((cos(t6) * FTx + sin(t6) * FTy) * (M_2PI * VAR(vibration2_freq)) + (cos(M_2PI * (t5 * VAR(vibration2_fmfreq))) * VAR(vibration2_fm) / VAR(vibration2_freq)) + (M_2PI * VAR(vibration2_phase) / VAR(vibration2_freq))) * (cos(M_2PI * (t5 * VAR(vibration2_amfreq))) * VAR(vibration2_am) * VAR(vibration2_amp) + VAR(vibration2_amp));
    FPx = (cos(t3) * t4 + (cos(t7) * t8 + FTx)) * VVAR + FPx;
    FPy = (t4 * sin(t3) + (t8 * sin(t7) + FTy)) * VVAR + FPy;
    return TRUE;
}