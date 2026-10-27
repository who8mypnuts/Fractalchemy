/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        Lozi.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from Lozi.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double lozi_a;
    double lozi_b;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("lozi");
APO_VARIABLES(
    VAR_REAL(lozi_a, 0.5),
    VAR_REAL(lozi_b, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    FPx = ((1.0 - (double)abs((int)FTx) * VAR(lozi_a)) + FTy) * VVAR + FPx;
    FPy = VAR(lozi_b) * FTx * VVAR + FPy;
    return TRUE;
}