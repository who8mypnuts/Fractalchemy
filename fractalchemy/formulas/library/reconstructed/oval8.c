/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        oval8.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from oval8.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {

} Variables;
#include "apoplugin.h"
APO_PLUGIN("oval8");
APO_VARIABLES(

);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTx * FTx;
    double t2 = VVAR * (t1 + 1e-20) * (cosh(FTy) * sin(FTx));
    double t3 = sinh(FTy) * cos(FTx) * (VVAR / (FTy * FTy + 0.5 * t1 + 1e-20)) + FPy;
    if (!(FTx > 0.0)) {
        FPx = FPx - t2;
        FPy = t3;
    } else {
        FPx = t2 + FPx;
        FPy = t3;
    }
    return TRUE;
}