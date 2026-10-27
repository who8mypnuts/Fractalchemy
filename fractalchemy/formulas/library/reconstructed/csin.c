/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        csin.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from csin.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double csin_stretch;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("csin");
APO_VARIABLES(
    VAR_REAL(csin_stretch, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = 0.0 * FTy;
    double t2 = t1 + FTx;
    double t3 = 0.0 * t2 + FTy * VAR(csin_stretch);
    double t4 = VAR(csin_stretch) * t2 - t1;
    FPx = VVAR * (cosh(t3) * sin(t4)) + FPx;
    FPy = VVAR * (sinh(t3) * cos(t4)) + FPy;
    return TRUE;
}