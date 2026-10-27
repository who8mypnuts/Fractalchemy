/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        dc_whorl.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from dc_whorl.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz', 32: 'TC'} var_base=88

typedef struct {
    double whorl_inside;
    double whorl_outside;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("dc_whorl2");
APO_VARIABLES(
    VAR_REAL(whorl_inside, 1.0),
    VAR_REAL(whorl_outside, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = sqrt(FTx * FTx + FTy * FTy);
    double t2 = VVAR * t1;
    double t3 = atan2(FTy, FTx);
    double t4 = VVAR - t1;
    double t5 = t3 + (VAR(whorl_outside) / t4);
    double t6 = t3 + (VAR(whorl_inside) / t4);
    if (VVAR > t1) {
        FPx = t2 * cos(t6) + FPx;
        FPy = t2 * sin(t6) + FPy;
        TC = fmod(0.25, 1.0);
    } else {
        FPx = t2 * cos(t5) + FPx;
        FPy = t2 * sin(t5) + FPy;
        TC = fmod(0.75, 1.0);
    }
    return TRUE;
}