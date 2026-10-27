/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        mask.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from mask.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {

} Variables;
#include "apoplugin.h"
APO_PLUGIN("mask");
APO_VARIABLES(

);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = cosh(FTy) + 1.0;
    double t2 = 1.0 / (FTy * FTy + FTx * FTx);
    double t3 = sin(FTx);
    double t4 = t3 * t3;
    FPx = t1 * (VVAR * t2 * t3) * t4;
    FPy = t1 * (t2 * VVAR * cos(FTx)) * t4;
    return TRUE;
}