/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        taurus.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from taurus.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double taurus_r;
    double taurus_n;
    double taurus_inv;
    double taurus_sor;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("taurus");
APO_VARIABLES(
    VAR_REAL(taurus_r, 3.0),
    VAR_REAL(taurus_n, 5.0),
    VAR_REAL(taurus_inv, 0.0),
    VAR_REAL(taurus_sor, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = cos(VAR(taurus_n) * FTx) * VAR(taurus_r) * (1.0 - VAR(taurus_inv)) + VAR(taurus_inv) * VAR(taurus_r) + sin(FTy);
    FPx = VVAR * (t1 * cos(FTx)) + FPx;
    FPy = VVAR * (t1 * sin(FTx)) + FPy;
    FPz = VVAR * (VAR(taurus_sor) * cos(FTy) + (1.0 - VAR(taurus_sor)) * FTy) + FPz;
    return TRUE;
}