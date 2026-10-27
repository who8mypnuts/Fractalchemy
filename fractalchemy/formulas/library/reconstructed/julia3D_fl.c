/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        julia3D_fl.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from julia3D_fl.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double julia3D_fl_power;
    double m_10;
    double m_8;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("julia3D_fl");
APO_VARIABLES(
    VAR_REAL(julia3D_fl_power, 2.0)
);

int PluginVarPrepare(Variation* vp)
{
    double t1 = 1.0 - VAR(julia3D_fl_power);
    double t2 = VAR(julia3D_fl_power) + VAR(julia3D_fl_power);
    double t3 = t1 * (1.0 / t2);
    if (!(VAR(julia3D_fl_power) >= -1.0)) {
        VAR(m_10) = VAR(julia3D_fl_power);
        VAR(m_8) = t3;
    } else {
        if (!(VAR(julia3D_fl_power) > 0.3333333333333333)) {
            VAR(m_10) = VAR(julia3D_fl_power);
            VAR(m_8) = t2 / t1;
        } else {
            VAR(m_10) = VAR(julia3D_fl_power);
            VAR(m_8) = t3;
        }
    }
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = fabs(VAR(m_10));
    double t2 = (1.0 / t1) * FTz;
    double t3 = FTy * FTy + FTx * FTx + 1e-05;
    double t4 = pow(t2 * t2 + t3, VAR(m_8)) * VVAR;
    double t5 = t2 * t4 + FPz;
    double t6 = fabs(VAR(m_10));
    double t7 = M_2PI * (double)(int)trunc(random01() * (t6 - 1e-05)) + atan2(FTy, FTx);
    double t8 = t7 * (1.0 / VAR(m_10));
    double t9 = cos(t8);
    double t10 = sqrt(t3);
    double t11 = t4 * t10;
    double t12 = sin(t8);
    double t13 = t7 * VAR(m_10);
    double t14 = cos(t13);
    double t15 = sin(t13);
    double t16 = t1 * FTz;
    double t17 = pow(t16 * t16 + t3, VAR(m_8)) * VVAR;
    double t18 = t16 * t17 + FPz;
    double t19 = t17 * t10;
    if (!(t1 > 1.0)) {
        if (!(t6 > 1.0)) {
            FPz = t18;
            FPx = t14 * t19 + FPx;
            FPy = t15 * t19 + FPy;
        } else {
            FPz = t18;
            FPx = t9 * t19 + FPx;
            FPy = t12 * t19 + FPy;
        }
    } else {
        if (!(t6 > 1.0)) {
            FPz = t5;
            FPx = t14 * t11 + FPx;
            FPy = t15 * t11 + FPy;
        } else {
            FPz = t5;
            FPx = t9 * t11 + FPx;
            FPy = t12 * t11 + FPy;
        }
    }
    return TRUE;
}