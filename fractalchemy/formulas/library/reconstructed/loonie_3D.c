/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        loonie_3D.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from loonie_3D.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double m_0;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("loonie_3D");
APO_VARIABLES(

);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_0) = VVAR * VVAR;
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTy * FTy + FTx * FTx;
    double t2 = atan2(FTy, FTx);
    double t3 = t1 + t2 * t2;
    double t4 = sqrt(VAR(m_0) / t3 - 1.0) * VVAR;
    double t5 = FTx * VVAR + FPx;
    double t6 = FTy * VVAR + FPy;
    double t7 = t1 + FTz * FTz;
    double t8 = sqrt(VAR(m_0) / t7 - 1.0) * VVAR;
    if (FTz != 0.0) {
        if (!(VAR(m_0) > t7)) {
            FPx = t5;
            FPy = t6;
            FPz = 0.5 * (FTz * VVAR) + FPz;
        } else {
            FPx = FTx * t8 + FPx;
            FPy = FTy * t8 + FPy;
            FPz = 0.5 * (FTz * t8) + FPz;
        }
    } else {
        if (!(VAR(m_0) > t3)) {
            FPx = t5;
            FPy = t6;
            FPz = 0.5 * (t2 * VVAR) + FPz;
        } else {
            FPx = FTx * t4 + FPx;
            FPy = FTy * t4 + FPy;
            FPz = 0.5 * (t2 * t4) + FPz;
        }
    }
    return TRUE;
}