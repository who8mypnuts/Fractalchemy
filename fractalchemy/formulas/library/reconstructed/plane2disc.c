/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        plane2disc_x86.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from plane2disc_x86.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    int cpow_power;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("plane2disc");
APO_VARIABLES(
    VAR_INTEGER(cpow_power, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = exp(0.25 * log(FTx * FTx + FTy * FTy));
    double t2 = t1 * t1;
    double t3 = 0.5 * atan2(FTy, FTx);
    double t4 = cos(t3) * t1;
    double t5 = VVAR / (t4 + t4 + (t2 + 1.0));
    FPx = 0.5 * (t2 + -1.0) * t5 + FPx;
    FPy = t5 * (t1 * sin(t3)) + FPy;
    return TRUE;
}