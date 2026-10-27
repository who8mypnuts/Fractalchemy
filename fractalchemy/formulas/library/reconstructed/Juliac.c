/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        Juliac.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from Juliac.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double juliac_re;
    double juliac_im;
    double juliac_dist;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("Juliac");
APO_VARIABLES(
    VAR_REAL(juliac_re, 2.0),
    VAR_REAL(juliac_im, 0.0),
    VAR_REAL(juliac_dist, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = log(FTx * FTx + FTy * FTy) * (0.5 * VAR(juliac_dist));
    double t2 = 1.0 / (VAR(juliac_re) + 1e-20);
    double t3 = fmod((double)rand(), 1.0 / t2);
    double t4 = M_PI * (t3 + t3) + atan2(FTy, FTx);
    double t5 = VAR(juliac_im) / 100.0;
    double t6 = VVAR * exp(t1 * t2 - t4 * t5);
    double t7 = t4 * t2 + t1 * t5;
    FPx = t6 * cos(t7) + FPx;
    FPy = t6 * sin(t7) + FPy;
    return TRUE;
}