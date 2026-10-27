/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        marblur.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from marblur.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {

} Variables;
#include "apoplugin.h"
APO_PLUGIN("marblur");
APO_VARIABLES(

);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = VVAR / (cosh(FTx * FTx + FTy * FTy) + 1e-20);
    if (2.0 > t1) {
        FPx = FTx * t1 + FPx;
        FPy = FTy * t1 + FPy;
    } else {
        FPx = VVAR * FTx + FPx;
        FPy = VVAR * FTy + FPy;
    }
    return TRUE;
}