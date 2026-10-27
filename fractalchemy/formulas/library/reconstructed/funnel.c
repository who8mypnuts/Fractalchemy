/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        funnel.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from funnel.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    int funnel_effect;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("funnel");
APO_VARIABLES(
    VAR_INTEGER(funnel_effect, 8)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTy + 1e-20;
    double t2 = 1.0 / cos(t1) + M_PI * VAR(funnel_effect);
    FPx = t2 * tanh(FTx + 1e-20) * VVAR + FPx;
    FPy = tanh(t1) * t2 * VVAR + FPy;
    return TRUE;
}