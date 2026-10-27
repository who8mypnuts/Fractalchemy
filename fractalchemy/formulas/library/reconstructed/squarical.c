/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        squarical.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from squarical.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double squarical_q1;
    double squarical_q2;
    double squarical_q3;
    double squarical_q4;
    double squarical_x;
    double squarical_y;
    double m_30;
    double m_38;
    double m_40;
    double m_48;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("squarical");
APO_VARIABLES(
    VAR_REAL(squarical_q1, 1.0),
    VAR_REAL(squarical_q2, 1.0),
    VAR_REAL(squarical_q3, 1.0),
    VAR_REAL(squarical_q4, 1.0),
    VAR_REAL(squarical_x, 1.0),
    VAR_REAL(squarical_y, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_30) = VVAR + VAR(squarical_q1);
    VAR(m_38) = VVAR + VAR(squarical_q2);
    VAR(m_40) = VVAR + VAR(squarical_q3);
    VAR(m_48) = VVAR + VAR(squarical_q4);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTx * VAR(squarical_x);
    double t2 = t1 * FTx;
    double t3 = FTy * FTy + FTx * FTx;
    double t4 = VAR(m_30) / t3;
    double t5 = FTy * VAR(squarical_y);
    double t6 = -t5 * FTy;
    double t7 = VAR(m_48) / t3;
    double t8 = t5 * FTy;
    double t9 = -t1 * FTx;
    double t10 = VAR(m_40) / t3;
    double t11 = VAR(m_38) / t3;
    if (!(FTx >= 0.0)) {
        if (!(FTy >= 0.0)) {
            FPx = t9 * t11 + FPx;
            FPy = t11 * t6 + FPy;
        } else {
            FPx = t9 * t10 + FPx;
            FPy = t10 * t8 + FPy;
        }
    } else {
        if (FTy >= 0.0) {
            FPx = t2 * t7 + FPx;
            FPy = t7 * t8 + FPy;
        } else {
            FPx = t2 * t4 + FPx;
            FPy = t4 * t6 + FPy;
        }
    }
    return TRUE;
}