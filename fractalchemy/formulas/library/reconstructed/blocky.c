/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        blocky.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from blocky.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double blocky_x;
    double blocky_y;
    double blocky_mp;
    double m_0;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("blocky");
APO_VARIABLES(
    VAR_REAL(blocky_x, 1.0),
    VAR_REAL(blocky_y, 1.0),
    VAR_REAL(blocky_mp, 4.0)
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
    double t5 = VVAR / ((cos(FTy) + cos(FTx)) / VAR(blocky_mp) + 1.0);
    double t6 = atan2(t3, sqrt(t4)) * VAR(m_0) * t5 * VAR(blocky_x) + FPx;
    double t7 = FTy + FTy;
    double t8 = FTy / (0.5 * (sqrt(t1 - t7) + sqrt(t1 + t7)));
    double t9 = 1.0 - t8 * t8;
    double t10 = atan2(t8, sqrt(t9)) * VAR(m_0) * t5 * VAR(blocky_y) + FPy;
    double t11 = atan2(t8, 0.0) * VAR(m_0) * t5 * VAR(blocky_y) + FPy;
    double t12 = atan2(t3, 0.0) * VAR(m_0) * t5 * VAR(blocky_x) + FPx;
    if (0.0 > t4) {
        if (0.0 > t9) {
            FPx = t12;
            FPy = t11;
        } else {
            FPx = t12;
            FPy = t10;
        }
    } else {
        if (0.0 > t9) {
            FPx = t6;
            FPy = t11;
        } else {
            FPx = t6;
            FPy = t10;
        }
    }
    return TRUE;
}