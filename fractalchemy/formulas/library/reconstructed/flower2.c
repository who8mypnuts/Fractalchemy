/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        flower2.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from flower2.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double flower2_petals;
    double flower2_holes;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("flower2");
APO_VARIABLES(
    VAR_REAL(flower2_petals, 2.0),
    VAR_REAL(flower2_holes, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = atan2(FTy, FTx);
    double t2 = cos(t1 * VAR(flower2_petals)) * (random01() - VAR(flower2_holes));
    FPx = VVAR * t2 * cos(t1) + FPx;
    FPy = t2 * VVAR * sin(t1) + FPy;
    return TRUE;
}