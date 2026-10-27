/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        squirrel.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from squirrel.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double squirrel_a;
    double squirrel_b;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("squirrel");
APO_VARIABLES(
    VAR_REAL(squirrel_a, 1.0),
    VAR_REAL(squirrel_b, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = sqrt(FTx * FTx * (VAR(squirrel_a) + 1e-20) + (VAR(squirrel_b) + 1e-20) * (FTy * FTy));
    FPx = tan(FTx) * cos(t1) * VVAR;
    FPy = tan(FTy) * sin(t1) * VVAR;
    return TRUE;
}