/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        roundspher3D.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from roundspher3D.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {

} Variables;
#include "apoplugin.h"
APO_PLUGIN("roundspher3D");
APO_VARIABLES(

);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTy * FTy + FTx * FTx;
    double t2 = 1.0 / (t1 + FTz * FTz);
    double t3 = VVAR * t2;
    double t4 = 1.0 / (t2 + 0.40528473456935116);
    double t5 = VVAR * (FTx * t3 * t4) + FPx;
    double t6 = VVAR * (t3 * FTy * t4) + FPy;
    double t7 = FTz * (t2 * VVAR) * t4 * VVAR;
    double t8 = cos(sqrt(t1));
    double t9 = 1.0 / (t1 + t8 * t8);
    double t10 = VVAR * t9;
    double t11 = 1.0 / (t9 + 0.40528473456935116);
    double t12 = VVAR * (FTx * t10 * t11) + FPx;
    double t13 = VVAR * (t10 * FTy * t11) + FPy;
    double t14 = t8 * (t9 * VVAR) * t11 * VVAR;
    if (!(FTz != 0.0)) {
        if (!(FPz != 0.0)) {
            FPx = t12;
            FPy = t13;
            FPz = t14 + t8;
        } else {
            FPx = t12;
            FPy = t13;
            FPz = t14 + FPz;
        }
    } else {
        if (!(FPz != 0.0)) {
            FPx = t5;
            FPy = t6;
            FPz = t7 + t8;
        } else {
            FPx = t5;
            FPy = t6;
            FPz = t7 + FPz;
        }
    }
    return TRUE;
}