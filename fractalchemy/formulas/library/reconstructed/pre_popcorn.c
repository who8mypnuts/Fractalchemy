/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        pre_popcorn.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from pre_popcorn.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double pre_popcorn_xr;
    double pre_popcorn_yr;
    double pre_popcorn_zr;
    double pre_popcorn_r;
    double pre_popcorn_n;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("pre_popcorn");
APO_VARIABLES(
    VAR_REAL(pre_popcorn_xr, 1.5),
    VAR_REAL(pre_popcorn_yr, 1.5),
    VAR_REAL(pre_popcorn_zr, 1.5),
    VAR_REAL(pre_popcorn_r, 3.0),
    VAR_REAL(pre_popcorn_n, 5.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTy * FTy;
    double t2 = FTx * FTx;
    double t3 = FTz * FTz;
    double t4 = 0.5 * VVAR * log(t1 + t2 + t3 + 1e-300);
    double t5 = cos(VAR(pre_popcorn_n) * FTx) * VAR(pre_popcorn_r) + cos(FTy);
    double t6 = sin(FTx);
    FPx = t4 * (sin(tan(t1 + t3 + 1e-300)) * VAR(pre_popcorn_xr) * (FTx * cos(FTx) * t5)) + FPx;
    FPy = t4 * (sin(tan(t2 + t3 + 1e-300)) * VAR(pre_popcorn_yr) * (FTx * t6 * t5)) + FPy;
    FPz = t4 * (cos(atan2(t1, t2)) * (VAR(pre_popcorn_zr) * t6) + FTx * sin(FTy)) + FPz;
    return TRUE;
}