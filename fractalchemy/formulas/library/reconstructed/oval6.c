/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        oval6.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from oval6.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {

} Variables;
#include "apoplugin.h"
APO_PLUGIN("oval6");
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
    double t3 = VVAR / (0.5 * t2 + t1 + 1e-20);
    double t4 = t1 * t3 * (cosh(FTy) * sin(FTx));
    double t5 = t4 + FPx;
    double t6 = t3 * t2;
    double t7 = sinh(FTy) * cos(FTx);
    double t8 = t6 * t7 + FPy;
    double t9 = FPy - t7 * t6;
    double t10 = FPx - t4;
    if (!(FTx > 0.0)) {
        if (FTy > 0.0) {
            FPx = t10;
            FPy = t8;
        } else {
            FPx = t10;
            FPy = t9;
        }
    } else {
        if (!(FTy > 0.0)) {
            FPx = t5;
            FPy = t9;
        } else {
            FPx = t5;
            FPy = t8;
        }
    }
    return TRUE;
}