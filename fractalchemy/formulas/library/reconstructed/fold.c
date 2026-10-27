/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        fold.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from fold.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double fold_size;
    double m_8;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("fold");
APO_VARIABLES(
    VAR_REAL(fold_size, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_8) = 0.1 * VVAR + sin(VAR(fold_size) + M_PI);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = sin(FTy) * VAR(m_8) + FPz;
    if (!(FTy > FTx)) {
        FPx = FTx * VAR(m_8) + FPx;
        FPy = ((FTy - FTx) + FTy) * VAR(m_8) + FPy;
        FPz = t1;
    } else {
        FPx = ((FTx - FTy) + FTx) * VAR(m_8) + FPx;
        FPy = FTy * VAR(m_8) + FPy;
        FPz = t1;
    }
    return TRUE;
}