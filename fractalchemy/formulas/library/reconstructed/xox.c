/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        xox.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from xox.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double xox_fesdfkla;
    double xox_dunno;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("xox");
APO_VARIABLES(
    VAR_REAL_CYCLE(xox_fesdfkla, -2.0, 2.0, 1.0),
    VAR_REAL_CYCLE(xox_dunno, -M_2PI, M_2PI, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTy / (sqrt(FTx * FTx + FTy * FTy) + 1e-20);
    double t2 = (1.0 / (asin(sin(t1) * VAR(xox_fesdfkla)) + 1e-20)) * t1 * VAR(xox_dunno);
    FPx = sin(t2) * -FTx * VVAR + FPx;
    FPy = cos(t2) * -FTy * VVAR + FPy;
    return TRUE;
}