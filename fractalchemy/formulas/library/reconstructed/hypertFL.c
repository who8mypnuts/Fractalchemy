/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        hypertFL.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from hypertFL.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double hypertFL_p;
    double hypertFL_q;
    double hypertFL_n;
    double m_18;
    double m_20;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("hypertFL");
APO_VARIABLES(
    VAR_REAL(hypertFL_p, 3.0),
    VAR_REAL(hypertFL_q, 7.0),
    VAR_REAL(hypertFL_n, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    double t1 = M_2PI / (VAR(hypertFL_p) + 1e-20);
    double t2 = cos(t1);
    double t3 = (1.0 - t2) * (1.0 / (cos(M_2PI / (VAR(hypertFL_q) + 1e-20)) + t2 + 1e-20)) + 1.0;
    double t4 = t1 * VAR(hypertFL_n);
    double t5 = cos(t4);
    double t6 = 1.0 / sqrt(t3 + 1e-20);
    double t7 = sin(t4);
    if (!(t3 > 0.0)) {
        VAR(m_18) = t5;
        VAR(m_20) = t7;
    } else {
        VAR(m_18) = t5 * t6;
        VAR(m_20) = t6 * t7;
    }
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTy - VAR(m_20);
    double t2 = FTx * VAR(m_20) + FTy * VAR(m_18);
    double t3 = FTx + VAR(m_18);
    double t4 = (VAR(m_18) * FTx - VAR(m_20) * FTy) + 1.0;
    double t5 = (1.0 / (t2 * t2 + t4 * t4 + 1e-20)) * VVAR;
    FPx = (t1 * t2 + t3 * t4) * t5 + FPx;
    FPy = (t4 * t1 - t2 * t3) * t5 + FPy;
    return TRUE;
}