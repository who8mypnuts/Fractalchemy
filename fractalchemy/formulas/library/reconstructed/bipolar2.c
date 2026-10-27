/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        bipolar2.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from bipolar2.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double bipolar2_r1;
    double bipolar2_a1;
    double bipolar2_r2;
    double bipolar2_a2;
    double m_20;
    double m_28;
    double m_30;
    double m_38;
    double m_40;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("bipolar2");
APO_VARIABLES(
    VAR_REAL(bipolar2_r1, 1.0),
    VAR_REAL(bipolar2_a1, 0.0),
    VAR_REAL(bipolar2_r2, 1.0),
    VAR_REAL(bipolar2_a2, 2.0)
);

int PluginVarPrepare(Variation* vp)
{
    double t1 = M_PI_2 * VAR(bipolar2_a1);
    double t2 = -VAR(bipolar2_r1);
    double t3 = M_PI_2 * VAR(bipolar2_a2);
    double t4 = -VAR(bipolar2_r2);
    VAR(m_20) = cos(t1) * t2;
    VAR(m_28) = sin(t1) * t2;
    VAR(m_30) = cos(t3) * t4;
    VAR(m_38) = sin(t3) * t4;
    VAR(m_40) = M_2_PI * VVAR;
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTx * VAR(m_38) + FTy * VAR(m_30);
    double t2 = VAR(m_30) * FTx + 1.0 - FTy * VAR(m_38);
    double t3 = atan2(t1, t2);
    double t4 = VAR(m_28) * FTx + VAR(m_20) * FTy;
    double t5 = VAR(m_20) * FTx + 1.0 - VAR(m_28) * FTy;
    double t6 = atan2(t4, t5);
    double t7 = 0.5 * log(t5 * t5 + t4 * t4);
    double t8 = 0.5 * log(t2 * t2 + t1 * t1);
    FPx = (VAR(m_38) * t3 + VAR(m_28) * t6 + VAR(m_20) * t7 + VAR(m_30) * t8) * VAR(m_40) + FPx;
    FPy = ((t3 * VAR(m_30) + t6 * VAR(m_20) - t7 * VAR(m_28)) - t8 * VAR(m_38)) * VAR(m_40) + FPy;
    return TRUE;
}