/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        Henon.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from Henon.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double henon_a;
    double henon_b;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("henon");
APO_VARIABLES(
    VAR_REAL(henon_a, 0.5),
    VAR_REAL(henon_b, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    FPx = ((1.0 - FTx * FTx * VAR(henon_a)) + FTy) * VVAR + FPx;
    FPy = VAR(henon_b) * FTx * VVAR + FPy;
    return TRUE;
}