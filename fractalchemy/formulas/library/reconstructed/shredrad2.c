/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        shredrad2_x86.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from shredrad2_x86.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    int shredrad2_n;
    double shredrad2_width;
    double shredrad2_power;
    double shredrad2_fan;
    double m_20;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("shredrad2");
APO_VARIABLES(
    VAR_INTEGER(shredrad2_n, 0),
    VAR_REAL(shredrad2_width, 1.0),
    VAR_REAL(shredrad2_power, 2.0),
    VAR_REAL(shredrad2_fan, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_20) = M_2PI / VAR(shredrad2_n);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = (atan2(FTy, FTx) + M_PI) / VAR(m_20) + 0.5;
    double t2 = t1 - (double)(int)t1;
    double t3 = exp(VAR(shredrad2_fan) * log(t2));
    double t4 = t3 + t3 - 1.0;
    double t5 = (double)(int)t1 + -0.5;
    double t6 = (t5 + 0.5 * (exp(VAR(shredrad2_power) * log(t4)) * VAR(shredrad2_width) + 1.0)) * VAR(m_20) - M_PI;
    double t7 = sqrt(FTx * FTx + FTy * FTy) * VVAR;
    double t8 = VVAR * FTz + FPz;
    double t9 = (t5 + 0.5 * (-exp(VAR(shredrad2_power) * log(-t4)) * VAR(shredrad2_width) + 1.0)) * VAR(m_20) - M_PI;
    double t10 = (t5 + 0.5 * (t4 * VAR(shredrad2_width) + 1.0)) * VAR(m_20) - M_PI;
    double t11 = t2 + t2 - 1.0;
    double t12 = (t5 + 0.5 * (exp(VAR(shredrad2_power) * log(t11)) * VAR(shredrad2_width) + 1.0)) * VAR(m_20) - M_PI;
    double t13 = (t5 + 0.5 * (-exp(VAR(shredrad2_power) * log(-t11)) * VAR(shredrad2_width) + 1.0)) * VAR(m_20) - M_PI;
    double t14 = (t5 + 0.5 * (t11 * VAR(shredrad2_width) + 1.0)) * VAR(m_20) - M_PI;
    if (!(VAR(shredrad2_fan) != 1.0)) {
        if (!(VAR(shredrad2_power) != 1.0)) {
            FPx = cos(t14) * t7 + FPx;
            FPy = sin(t14) * t7 + FPy;
            FPz = t8;
        } else {
            if (!(t11 > 0.0)) {
                FPx = cos(t13) * t7 + FPx;
                FPy = sin(t13) * t7 + FPy;
                FPz = t8;
            } else {
                FPx = cos(t12) * t7 + FPx;
                FPy = sin(t12) * t7 + FPy;
                FPz = t8;
            }
        }
    } else {
        if (!(VAR(shredrad2_power) != 1.0)) {
            FPx = cos(t10) * t7 + FPx;
            FPy = sin(t10) * t7 + FPy;
            FPz = t8;
        } else {
            if (!(t4 > 0.0)) {
                FPx = cos(t9) * t7 + FPx;
                FPy = sin(t9) * t7 + FPy;
                FPz = t8;
            } else {
                FPx = cos(t6) * t7 + FPx;
                FPy = sin(t6) * t7 + FPy;
                FPz = t8;
            }
        }
    }
    return TRUE;
}