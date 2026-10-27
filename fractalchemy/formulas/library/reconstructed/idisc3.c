/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        idisc3.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from idisc3.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double idisc3_limit;
    int idisc3_fix;
    double m_0;
    double m_8;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("idisc3");
APO_VARIABLES(
    VAR_REAL(idisc3_limit, 0.5),
    VAR_INTEGER_NONZERO(idisc3_fix, 1)
);

int PluginVarPrepare(Variation* vp)
{
    double t1 = M_1_PI * VVAR;
    if (VAR(idisc3_fix) != 0) {
        VAR(m_0) = t1;
        VAR(m_8) = M_PI / log(fabs(VAR(idisc3_limit)) + 1e-10);
    } else {
        VAR(m_0) = t1;
        VAR(m_8) = M_PI;
    }
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = log(fabs(VAR(idisc3_limit)) + 1e-10 + FTx * FTx + FTy * FTy) * VAR(m_8);
    double t2 = atan2(FTy, FTx) * VAR(m_0);
    FPx = cos(t1) * t2 + FPx;
    FPy = sin(t1) * t2 + FPy;
    return TRUE;
}