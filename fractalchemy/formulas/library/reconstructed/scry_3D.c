/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        scry_3D.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from scry_3D.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double m_0;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("scry_3D");
APO_VARIABLES(

);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_0) = 1.0 / (VVAR + 1e-20);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTx * VVAR;
    double t2 = FTy * FTy + FTx * FTx;
    double t3 = fabs(VAR(m_0));
    double t4 = sqrt(t2);
    double t5 = -1.0 / ((t2 + t3) * t4);
    double t6 = t1 * t5 + FPx;
    double t7 = FTy * VVAR;
    double t8 = t5 * t7 + FPy;
    double t9 = 0.0 * FPz;
    double t10 = cos(t4);
    double t11 = t10 * t10 + t4;
    double t12 = sqrt(t11);
    double t13 = t10 * (-1.0 / ((t11 + t3) * t12));
    double t14 = (t13 + t10) * VVAR;
    double t15 = (1.0 - VVAR) * FPz;
    double t16 = 1.0 / ((t2 + VAR(m_0)) * t4);
    double t17 = t1 * t16 + FPx;
    double t18 = t16 * t7 + FPy;
    double t19 = t10 * (1.0 / (t12 * (t11 + VAR(m_0))));
    double t20 = (t19 + t10) * VVAR;
    double t21 = FTz * FTz + t4;
    double t22 = sqrt(t21);
    double t23 = FTz * (-1.0 / ((t21 + t3) * t22));
    double t24 = (t23 + t10) * VVAR;
    double t25 = FTz * (1.0 / (t22 * (t21 + VAR(m_0))));
    double t26 = (t25 + t10) * VVAR;
    double t27 = (t13 + FPz) * VVAR;
    double t28 = (t19 + FPz) * VVAR;
    double t29 = (t23 + FPz) * VVAR;
    double t30 = (t25 + FPz) * VVAR;
    if (FPz != 0.0) {
        if (FTz != 0.0) {
            if (VAR(m_0) >= 0.0) {
                if (!(fabs(VVAR) > 1.0)) {
                    FPx = t17;
                    FPy = t18;
                    FPz = t15 + t30;
                } else {
                    FPx = t17;
                    FPy = t18;
                    FPz = t9 + t30;
                }
            } else {
                if (!(fabs(VVAR) > 1.0)) {
                    FPx = t6;
                    FPy = t8;
                    FPz = t15 + t29;
                } else {
                    FPx = t6;
                    FPy = t8;
                    FPz = t9 + t29;
                }
            }
        } else {
            if (VAR(m_0) >= 0.0) {
                if (!(fabs(VVAR) > 1.0)) {
                    FPx = t17;
                    FPy = t18;
                    FPz = t15 + t28;
                } else {
                    FPx = t17;
                    FPy = t18;
                    FPz = t9 + t28;
                }
            } else {
                if (!(fabs(VVAR) > 1.0)) {
                    FPx = t6;
                    FPy = t8;
                    FPz = t15 + t27;
                } else {
                    FPx = t6;
                    FPy = t8;
                    FPz = t9 + t27;
                }
            }
        }
    } else {
        if (FTz != 0.0) {
            if (VAR(m_0) >= 0.0) {
                if (!(fabs(VVAR) > 1.0)) {
                    FPx = t17;
                    FPy = t18;
                    FPz = t15 + t26;
                } else {
                    FPx = t17;
                    FPy = t18;
                    FPz = t9 + t26;
                }
            } else {
                if (!(fabs(VVAR) > 1.0)) {
                    FPx = t6;
                    FPy = t8;
                    FPz = t15 + t24;
                } else {
                    FPx = t6;
                    FPy = t8;
                    FPz = t9 + t24;
                }
            }
        } else {
            if (VAR(m_0) >= 0.0) {
                if (!(fabs(VVAR) > 1.0)) {
                    FPx = t17;
                    FPy = t18;
                    FPz = t15 + t20;
                } else {
                    FPx = t17;
                    FPy = t18;
                    FPz = t9 + t20;
                }
            } else {
                if (!(fabs(VVAR) > 1.0)) {
                    FPx = t6;
                    FPy = t8;
                    FPz = t15 + t14;
                } else {
                    FPx = t6;
                    FPy = t8;
                    FPz = t9 + t14;
                }
            }
        }
    }
    return TRUE;
}