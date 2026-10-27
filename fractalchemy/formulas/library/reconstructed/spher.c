/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        Spher.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from Spher.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {

} Variables;
#include "apoplugin.h"
APO_PLUGIN("spher");
APO_VARIABLES(

);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTx * FTx + FTy * FTy;
    double t2 = random01();
    double t3 = 10000000.0 * t2;
    double t4 = t3 + FPx;
    double t5 = t3 + FPy;
    double t6 = VVAR * FTx;
    double t7 = VVAR * FTy;
    double t8 = t6 / t1;
    double t9 = t7 / t1;
    if (t1 >= VVAR * VVAR) {
        if (0.5 > t2) {
            if (1e-06 > t8 * t8 + t9 * t9) {
                FPx = t4;
                FPy = t5;
            } else {
                FPx = FPx + t8;
                FPy = FPy + t9;
            }
        } else {
            FPx = t6 + FPx;
            FPy = t7 + FPy;
        }
    } else {
        FPx = t4;
        FPy = t5;
    }
    return TRUE;
}