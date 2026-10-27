/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        sinecho.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from sinecho.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double sinecho_q1;
    double sinecho_q2;
    double sinecho_q3;
    double sinecho_q4;
    double m_20;
    double m_28;
    double m_30;
    double m_38;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("sinecho");
APO_VARIABLES(
    VAR_REAL(sinecho_q1, 1.0),
    VAR_REAL(sinecho_q2, 1.0),
    VAR_REAL(sinecho_q3, 1.0),
    VAR_REAL(sinecho_q4, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_20) = VVAR * VAR(sinecho_q1);
    VAR(m_28) = VVAR * VAR(sinecho_q2);
    VAR(m_30) = VVAR * VAR(sinecho_q3);
    VAR(m_38) = VVAR * VAR(sinecho_q4);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = sin(FTx);
    double t2 = -VAR(m_20);
    double t3 = sin(FTy);
    double t4 = FTy + FTz;
    double t5 = -VAR(m_38);
    double t6 = -VAR(m_30);
    double t7 = -VAR(m_28);
    if (!(random01() > 0.5)) {
        if (!(FTx >= 0.0)) {
            if (!(FTy >= 0.0)) {
                FPx = t1 * VAR(m_28) + FPx;
                FPy = t3 * VAR(m_28) + FPy;
                FPz = VAR(m_28) * t4 + FPz;
            } else {
                FPx = t1 * VAR(m_30) + FPx;
                FPy = t3 * VAR(m_30) + FPy;
                FPz = VAR(m_30) * t4 + FPz;
            }
        } else {
            if (FTy >= 0.0) {
                FPx = t1 * VAR(m_38) + FPx;
                FPy = t3 * VAR(m_38) + FPy;
                FPz = VAR(m_38) * t4 + FPz;
            } else {
                FPx = t1 * VAR(m_20) + FPx;
                FPy = t3 * VAR(m_20) + FPy;
                FPz = VAR(m_20) * t4 + FPz;
            }
        }
    } else {
        if (!(FTx >= 0.0)) {
            if (!(FTy >= 0.0)) {
                FPx = t1 * t7 + FPx;
                FPy = t3 * t7 + FPy;
                FPz = t7 * t4 + FPz;
            } else {
                FPx = t1 * t6 + FPx;
                FPy = t3 * t6 + FPy;
                FPz = t6 * t4 + FPz;
            }
        } else {
            if (FTy >= 0.0) {
                FPx = t1 * t5 + FPx;
                FPy = t3 * t5 + FPy;
                FPz = t5 * t4 + FPz;
            } else {
                FPx = t1 * t2 + FPx;
                FPy = t3 * t2 + FPy;
                FPz = t2 * t4 + FPz;
            }
        }
    }
    return TRUE;
}