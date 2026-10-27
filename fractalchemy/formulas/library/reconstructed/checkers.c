/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        checkers.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from checkers.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {

} Variables;
#include "apoplugin.h"
APO_PLUGIN("checkers");
APO_VARIABLES(

);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = VVAR * FTx;
    double t2 = VVAR * FTy + FPy;
    if (((int)(5.0 * FTy + 0.5) + (int)(5.0 * FTx + 0.5) & 1) == 0) {
        FPx = t1 + (double)0 + FPx;
        FPy = t2;
    } else {
        FPx = t1 + (double)1045220557 + FPx;
        FPy = t2;
    }
    return TRUE;
}