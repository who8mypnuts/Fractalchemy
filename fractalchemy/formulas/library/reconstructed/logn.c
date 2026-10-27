/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        logn.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from logn.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double logn_base;
    double m_8;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("logn");
APO_VARIABLES(
    VAR_REAL(logn_base, M_E)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_8) = log(VAR(logn_base));
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    FPx = log(FTx * FTx + FTy * FTy) * (0.5 * VVAR) / VAR(m_8) + FPx;
    FPy = atan2(FTy, FTx) * VVAR + FPy;
    return TRUE;
}