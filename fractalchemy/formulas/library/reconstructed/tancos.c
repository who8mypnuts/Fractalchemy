/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        tancos.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from tancos.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {

} Variables;
#include "apoplugin.h"
APO_PLUGIN("tancos");
APO_VARIABLES(

);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTx * FTx + FTy * FTy;
    double t2 = t1 + 1e-20;
    double t3 = 1.0 / t1;
    double t4 = tanh(t2) * FTx * (VVAR * t3 + 1e-20);
    double t5 = cos(t2) * FTy * (t3 * VVAR + 1e-20);
    FPx = t4 + t4 + FPx;
    FPy = t5 + t5 + FPy;
    return TRUE;
}