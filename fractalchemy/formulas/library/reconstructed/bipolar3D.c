/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        Bipolar3D.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from Bipolar3D.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double b_shift_3D;
    double m_10;
    double m_18;
    double m_8;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("bipolar3D");
APO_VARIABLES(
    VAR_REAL_CYCLE(b_shift_3D, -1.0, 1.0, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_8) = M_2_PI * (0.25 * VVAR);
    VAR(m_10) = M_2_PI * VVAR;
    VAR(m_18) = -M_PI_2 * VAR(b_shift_3D);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTy * FTy + FTx * FTx;
    double t2 = 0.5 * atan2(FTy + FTy, t1 - 1.0) + VAR(m_18);
    double t3 = t1 + 1.0;
    double t4 = FTx + FTx;
    double t5 = log((t3 + t4) / (t3 - t4)) * VAR(m_8) + FPx;
    double t6 = VVAR * FTz + FPz;
    if (t2 > M_PI_2) {
        FPx = t5;
        FPy = VAR(m_10) * (fmod(t2 + M_PI_2, M_PI) + -M_PI_2) + FPy;
        FPz = t6;
    } else {
        if (-M_PI_2 > t2) {
            FPx = t5;
            FPy = VAR(m_10) * (M_PI_2 - fmod(M_PI_2 - t2, M_PI)) + FPy;
            FPz = t6;
        } else {
            FPx = t5;
            FPy = VAR(m_10) * t2 + FPy;
            FPz = t6;
        }
    }
    return TRUE;
}