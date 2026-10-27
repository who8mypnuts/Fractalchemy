/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        dc_twoface.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from dc_twoface.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz', 32: 'TC'} var_base=88

typedef struct {

} Variables;
#include "apoplugin.h"
APO_PLUGIN("dc_twoface");
APO_VARIABLES(

);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = VVAR * (1.0 / sqrt(FTy * FTy + FTx * FTx));
    double t2 = atan2(FTy, FTx);
    if (FTx > 0.0) {
        FPx = t1 * cos(t2) + FPx;
        FPy = t1 * sin(t2) + FPy;
        TC = fmod(TC + 0.25, 1.0);
    } else {
        FPx = VVAR * FTx + FPx;
        FPy = VVAR * FTy + FPy;
        TC = fmod(TC + 0.75, 1.0);
    }
    return TRUE;
}