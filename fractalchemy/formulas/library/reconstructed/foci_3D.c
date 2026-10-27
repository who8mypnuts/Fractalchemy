/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        foci_3D.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from foci_3D.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {

} Variables;
#include "apoplugin.h"
APO_PLUGIN("foci_3D");
APO_VARIABLES(

);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = 0.5 * exp(FTx);
    double t2 = 0.25 / t1;
    double t3 = t1 - t2;
    double t4 = t1 + t2;
    double t5 = atan2(FTy, FTx);
    double t6 = cos(FTy);
    double t7 = (1.0 / (t4 - cos(t5) * t6)) * VVAR;
    double t8 = sin(FTy);
    double t9 = (1.0 / (t4 - cos(FTz) * t6)) * VVAR;
    if (FTz != 0.0) {
        FPx = t3 * t9 + FPx;
        FPy = t8 * t9 + FPy;
        FPz = t9 * sin(FTz) + FPz;
    } else {
        FPx = t3 * t7 + FPx;
        FPy = t8 * t7 + FPy;
        FPz = t7 * sin(t5) + FPz;
    }
    return TRUE;
}