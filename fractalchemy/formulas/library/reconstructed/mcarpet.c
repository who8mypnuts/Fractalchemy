/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        mcarpet.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from mcarpet.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double mcarpet_x;
    double mcarpet_y;
    double mcarpet_twist;
    double mcarpet_tilt;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("mcarpet");
APO_VARIABLES(
    VAR_REAL(mcarpet_x, 1.0),
    VAR_REAL(mcarpet_y, 1.0),
    VAR_REAL(mcarpet_twist, 0.0),
    VAR_REAL(mcarpet_tilt, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTx * FTx;
    double t2 = VVAR / ((FTy * FTy + t1) / 4.0 + 1.0);
    double t3 = FTx * t2 * VAR(mcarpet_x) + FPx;
    double t4 = FTy * t2 * VAR(mcarpet_y) + FPy;
    FPx = ((1.0 - t1 * VAR(mcarpet_twist)) + FTy) * VVAR + t3;
    FPy = VAR(mcarpet_tilt) * FTx * VVAR + t4;
    return TRUE;
}