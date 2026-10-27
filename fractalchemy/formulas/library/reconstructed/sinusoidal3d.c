/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        sinusoidal3d.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from sinusoidal3d.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {

} Variables;
#include "apoplugin.h"
APO_PLUGIN("sinusoidal3d");
APO_VARIABLES(

);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    FPx = sin(FTx) * VVAR + FPx;
    FPy = sin(FTy) * VVAR + FPy;
    FPz = cos(FTz) * atan2(FTx * FTx, FTy * FTy) * VVAR + FPz;
    return TRUE;
}