/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        ho.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from ho.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double ho_xpow;
    double ho_ypow;
    double ho_zpow;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("ho");
APO_VARIABLES(
    VAR_REAL(ho_xpow, 3.0),
    VAR_REAL(ho_ypow, 3.0),
    VAR_REAL(ho_zpow, 3.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = cos(FTy);
    double t2 = cos(FTx) * t1;
    double t3 = FTz * FTz;
    double t4 = sin(FTx) * t1;
    double t5 = sin(FTy);
    FPx = VVAR * (pow(t2, VAR(ho_xpow)) + t2 * VAR(ho_xpow) + 0.25 * atan2(FTy * FTy, t3)) + FPx;
    FPy = VVAR * (pow(t4, VAR(ho_ypow)) + t4 * VAR(ho_ypow) + 0.25 * atan2(FTx * FTx, t3)) + FPy;
    FPz = VVAR * (pow(t5, VAR(ho_zpow)) + VAR(ho_zpow) * t5) + FPz;
    return TRUE;
}