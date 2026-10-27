/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        parabola2.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from parabola2.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double parabola2_height;
    double parabola2_width;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("parabola2");
APO_VARIABLES(
    VAR_REAL(parabola2_height, 1.0),
    VAR_REAL(parabola2_width, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = sqrt(FTy * FTy + FTx * FTx + 1e-20);
    double t2 = sin(t1);
    FPx = random01() * (VAR(parabola2_height) * VVAR * (t2 * t2)) + FPx;
    FPy = 16777216 * (double)((rand() ^ rand() << 15) & 268435455) * (VAR(parabola2_width) * VVAR * cos(t1)) + FPy;
    return TRUE;
}