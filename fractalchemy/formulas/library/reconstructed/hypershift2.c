/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        hypershift2_x86.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from hypershift2_x86.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    int hypershift2_p;
    int hypershift2_q;
    double m_0;
    double m_10;
    double m_8;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("hypershift2");
APO_VARIABLES(
    VAR_INTEGER_NONZERO(hypershift2_p, 3),
    VAR_INTEGER_NONZERO(hypershift2_q, 7)
);

int PluginVarPrepare(Variation* vp)
{
    double t1 = M_PI / (double)VAR(hypershift2_q);
    double t2 = M_PI / (double)VAR(hypershift2_p);
    double t3 = sin(t2);
    double t4 = sin(t1);
    double t5 = t4 * t4;
    double t6 = sin(M_PI_2 - (t1 + t2)) / sqrt(1.0 - (t3 * t3 + t5));
    double t7 = sin(t2 + M_PI_2);
    VAR(m_0) = t6;
    VAR(m_8) = 1.0 - t6 * t6;
    VAR(m_10) = (t7 / t4 + -1.0) * (1.0 / sqrt(t7 * t7 / t5 - 1.0));
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = M_PI * ((double)(rand() % VAR(hypershift2_p)) + (double)(rand() % VAR(hypershift2_p)) + 1.0) / (double)VAR(hypershift2_p);
    double t2 = cos(t1);
    double t3 = FTx * VAR(m_10);
    double t4 = VAR(m_10) * FTy;
    double t5 = 1.0 / (t3 * t3 + t4 * t4);
    double t6 = t3 * t5 + VAR(m_0);
    double t7 = t4 * t5;
    double t8 = VAR(m_8) * VVAR / (t7 * t7 + t6 * t6);
    double t9 = t6 * t8 + VAR(m_0);
    double t10 = sin(t1);
    double t11 = t7 * t8;
    FPx = t2 * t9 - t10 * t11;
    FPy = t11 * t2 + t9 * t10;
    FPz = t8 * FTz;
    return TRUE;
}