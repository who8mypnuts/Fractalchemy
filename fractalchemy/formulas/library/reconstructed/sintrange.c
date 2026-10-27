/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        sintrange.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from sintrange.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz', 32: 'TC'} var_base=88

typedef struct {
    double sintrange_w;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("sintrange");
APO_VARIABLES(
    VAR_REAL(sintrange_w, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTx * FTx;
    double t2 = FTy * FTy;
    double t3 = (t2 + t1) * VAR(sintrange_w);
    FPx = sin(FTx) * VVAR * (t1 + VAR(sintrange_w) - t3);
    FPy = sin(FTy) * VVAR * (t2 + VAR(sintrange_w) - t3);
    return TRUE;
}