/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        hearty.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from hearty.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {

} Variables;
#include "apoplugin.h"
APO_PLUGIN("hearty");
APO_VARIABLES(

);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = sqrt(FTx * FTx + FTy * FTy);
    double t2 = isnan(t1 + t1);
    double t3 = atan2(FTy, FTx);
    double t4 = sin(t3);
    double t5 = t1 * VVAR;
    double t6 = fabs(t4) * -t4 * t5 + FPx;
    double t7 = FPy - (((0.8125 * cos(t3) - 0.3125 * cos(t3 + t3)) - 0.125 * cos(3.0 * t3)) - 0.0625 * cos(4.0 * t3)) * t5;
    FPx = t6;
    FPy = t7;
    return TRUE;
}