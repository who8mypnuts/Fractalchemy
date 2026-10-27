/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        spikes.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from spikes.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {

} Variables;
#include "apoplugin.h"
APO_PLUGIN("spikes");
APO_VARIABLES(

);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = sqrt(FTy * FTy + FTx * FTx);
    double t2 = 1.0471975511965976 * (double)(int)rint(10.0 * random01());
    double t3 = rint(FTx);
    double t4 = sin(t2) * (FTx - t3);
    double t5 = 1.0 / t1;
    double t6 = VVAR * t5;
    double t7 = t5 * VVAR;
    double t8 = rint(FTy);
    double t9 = cos(t2) * (FTy - t8);
    if (!((double)(int)rint(0.5 * t1) != 0.0)) {
        FPx = (t4 - t3) * t6 + FPx;
        FPy = t7 * (t9 - t8) + FPy;
    } else {
        FPx = (t4 + t3) * t6 + FPx;
        FPy = t7 * (t9 + t8) + FPy;
    }
    return TRUE;
}