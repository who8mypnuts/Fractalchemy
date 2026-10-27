/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        fourth.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from fourth.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz', 32: 'TC'} var_base=88

typedef struct {
    double fourth_spin;
    double fourth_space;
    double fourth_twist;
    double fourth_x;
    double fourth_y;
    double m_0;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("fourth");
APO_VARIABLES(
    VAR_REAL_CYCLE(fourth_spin, 0.0, M_2PI, M_PI),
    VAR_REAL(fourth_space, 0.0),
    VAR_REAL(fourth_twist, 0.0),
    VAR_REAL(fourth_x, 0.0),
    VAR_REAL(fourth_y, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_0) = VVAR * VVAR;
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = VVAR * FTx + FPx;
    double t2 = VVAR * FTy + FPy;
    double t3 = FTx - VAR(fourth_x);
    double t4 = FTy + VAR(fourth_y);
    double t5 = sqrt(t3 * t3 + t4 * t4);
    double t6 = (VAR(fourth_space) / t5 + 1.0) * VVAR;
    double t7 = t5 * VVAR;
    double t8 = atan2(t4, t3) + VAR(fourth_spin) + (VVAR - t5) * VAR(fourth_twist);
    double t9 = FTy * FTy + FTx * FTx;
    double t10 = sqrt(VAR(m_0) / t9 - 1.0) * VVAR;
    double t11 = VVAR * (1.0 / sqrt(t9));
    double t12 = atan2(FTy, FTx);
    if (FTx > 0.0) {
        if (FTy > 0.0) {
            FPx = t11 * cos(t12) + FPx;
            FPy = t11 * sin(t12) + FPy;
        } else {
            if (0.0 > FTy) {
                if (VAR(m_0) > t9) {
                    FPx = FTx * t10 + FPx;
                    FPy = FTy * t10 + FPy;
                } else {
                    FPx = t1;
                    FPy = t2;
                }
            } else {
                FPx = t1;
                FPy = t2;
            }
        }
    } else {
        if (0.0 > FTx) {
            if (FTy > 0.0) {
                if (VVAR > t5) {
                    FPx = t7 * cos(t8) + VAR(fourth_x) + FPx;
                    FPy = (t7 * sin(t8) - VAR(fourth_y)) + FPy;
                } else {
                    FPx = t6 * t3 + VAR(fourth_x) + FPx;
                    FPy = (t6 * t4 - VAR(fourth_y)) + FPy;
                }
            } else {
                FPx = t1;
                FPy = t2;
            }
        } else {
            FPx = t1;
            FPy = t2;
        }
    }
    return TRUE;
}