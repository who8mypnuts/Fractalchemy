/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        csch.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from csch.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {

} Variables;
#include "apoplugin.h"
APO_PLUGIN("csch");
APO_VARIABLES(

);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = 1.0 / (cosh(FTx + FTx) - cos(FTy + FTy));
    double t2 = t1 + t1;
    double t3 = exp(FTx);
    double t4 = 1.0 / t3;
    FPx = VVAR * t2 * (0.5 * (t3 - t4)) * cos(FTy) + FPx;
    FPy = 0.5 * (t4 + t3) * -(t2 * VVAR) * sin(FTy) + FPy;
    return TRUE;
}