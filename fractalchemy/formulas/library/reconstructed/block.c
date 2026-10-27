/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        block.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from block.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double m_0;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("block");
APO_VARIABLES(

);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_0) = VVAR / M_PI_2;
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTx * FTx + FTy * FTy + 1.0;
    double t2 = FTx + FTx;
    double t3 = FTx / (0.5 * (sqrt(t1 - t2) + sqrt(t1 + t2)));
    double t4 = 1.0 - t3 * t3;
    double t5 = atan2(t3, sqrt(t4)) * VAR(m_0) + FPx;
    double t6 = FTy + FTy;
    double t7 = FTy / (0.5 * (sqrt(t1 - t6) + sqrt(t1 + t6)));
    double t8 = 1.0 - t7 * t7;
    double t9 = atan2(t7, sqrt(t8)) * VAR(m_0) + FPy;
    double t10 = atan2(t7, 0.0) * VAR(m_0) + FPy;
    double t11 = atan2(t3, 0.0) * VAR(m_0) + FPx;
    if (0.0 > t4) {
        if (0.0 > t8) {
            FPx = t11;
            FPy = t10;
        } else {
            FPx = t11;
            FPy = t9;
        }
    } else {
        if (0.0 > t8) {
            FPx = t5;
            FPy = t10;
        } else {
            FPx = t5;
            FPy = t9;
        }
    }
    return TRUE;
}