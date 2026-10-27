/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        oval1.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from oval1.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {

} Variables;
#include "apoplugin.h"
APO_PLUGIN("oval1");
APO_VARIABLES(

);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = sin(FTx);
    double t2 = FTx * FTx;
    double t3 = FTy * FTy;
    FPx = cosh(FTy) * t1 * (VVAR / (t2 / (t1 + 1e-20) + t3 + 1e-20)) + FPx;
    FPy = sinh(FTy) * cos(FTx) * (VVAR / (t3 / (sin(FTy) + 1e-20) + t2 + 1e-20)) + FPy;
    return TRUE;
}