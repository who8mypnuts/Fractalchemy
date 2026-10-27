/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        roundspher.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from roundspher.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {

} Variables;
#include "apoplugin.h"
APO_PLUGIN("roundspher");
APO_VARIABLES(

);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = 1.0 / (FTy * FTy + FTx * FTx);
    double t2 = 1.0 / (t1 + 0.40528473456935116);
    FPx = VVAR * (FTx * (VVAR * t1) * t2) + FPx;
    FPy = VVAR * (t2 * (t1 * VVAR * FTy)) + FPy;
    return TRUE;
}