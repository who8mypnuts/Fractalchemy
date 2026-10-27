/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        shamrock.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from shamrock.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {

} Variables;
#include "apoplugin.h"
APO_PLUGIN("shamrock");
APO_VARIABLES(

);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTy * FTy;
    double t2 = FTx * FTx;
    double t3 = VVAR / (t1 * t1 + t2 * t2 + 1e-20);
    double t4 = t3 + t3;
    if (2.0 > t4) {
        FPx = FTx * t4 + FPx;
        FPy = FTy * t4 + FPy;
    } else {
        FPx = VVAR * FTx + FPx;
        FPy = VVAR * FTy + FPy;
    }
    return TRUE;
}