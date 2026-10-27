/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        depth_gaussian_x86.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from depth_gaussian_x86.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double dg_blur;
    double dg_radius;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("depth_gaussian");
APO_VARIABLES(
    VAR_REAL(dg_blur, 1.0),
    VAR_REAL(dg_radius, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = sqrt(FTy * FTy + FTx * FTx);
    double t2 = 0.1 * VAR(dg_blur) * (t1 - VAR(dg_radius)) * sqrt(-2.0 * log(random01()));
    double t3 = 2.3406689355471266e-08 * (double)((rand() ^ rand() << 15) & 268435455);
    if (t1 > VAR(dg_radius)) {
        FPx = (t2 * cos(t3) + FTx) * VVAR + FPx;
        FPy = (sin(t3) * t2 + FTy) * VVAR + FPy;
    } else {
        FPx = FTx * VVAR + FPx;
        FPy = FTy * VVAR + FPy;
    }
    return TRUE;
}