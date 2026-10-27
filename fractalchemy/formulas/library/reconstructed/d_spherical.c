/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        d_spherical_x86.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from d_spherical_x86.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double d_spher_weight;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("d_spherical");
APO_VARIABLES(
    VAR_REAL(d_spher_weight, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = VVAR / (FTx * FTx + FTy * FTy);
    if (random01() < VAR(d_spher_weight)) {
        FPx = FTx * t1 + FPx;
        FPy = t1 * FTy + FPy;
    } else {
        FPx = FTx * VVAR + FPx;
        FPy = FTy * VVAR + FPy;
    }
    return TRUE;
}