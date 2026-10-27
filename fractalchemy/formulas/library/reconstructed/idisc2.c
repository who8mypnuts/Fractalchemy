/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        idisc2.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from idisc2.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double idisc2_limit;
    double m_0;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("idisc2");
APO_VARIABLES(
    VAR_REAL(idisc2_limit, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_0) = M_1_PI * VVAR;
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = M_PI * VAR(idisc2_limit) / (fabs(VAR(idisc2_limit)) + 1e-60 + FTx * FTx + FTy * FTy);
    double t2 = atan2(FTy, FTx) * VAR(m_0);
    FPx = cos(t1) * t2 + FPx;
    FPy = sin(t1) * t2 + FPy;
    return TRUE;
}