/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        smartshape.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from smartshape.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double sshape_power;
    double sshape_roundstr;
    double sshape_roundwidth;
    double sshape_distortion;
    int sshape_compensation;
    double m_20;
    double m_28;
    double m_30;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("smartshape");
APO_VARIABLES(
    VAR_REAL(sshape_power, 4.0),
    VAR_REAL(sshape_roundstr, 0.0),
    VAR_REAL(sshape_roundwidth, 1.0),
    VAR_REAL(sshape_distortion, 1.0),
    VAR_INTEGER_NONZERO(sshape_compensation, 0)
);

int PluginVarPrepare(Variation* vp)
{
    double t1 = M_2PI / VAR(sshape_power);
    double t2 = 0.5 * t1;
    double t3 = tan(t2);
    double t4 = VAR(sshape_roundstr) / (VAR(sshape_power) * sin(t2));
    if (VAR(sshape_power) >= 2.0) {
        VAR(m_20) = t1;
        VAR(m_30) = t3 + t3;
        VAR(m_28) = t4 + t4;
    } else {
        VAR(sshape_power) = 2.0;
        VAR(m_20) = M_PI;
        VAR(m_30) = 3.266247870639074e+16;
        VAR(m_28) = VAR(sshape_roundstr);
    }
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = (atan2(FTy, FTx) + M_PI) / VAR(m_20);
    double t2 = t1 - (double)(int)t1;
    double t3 = 1.0 - t2;
    double t4 = 1.0 / cos(VAR(m_20) * t3);
    double t5 = exp(VAR(sshape_distortion) * log(t4)) * VVAR;
    double t6 = FTz * VVAR + FPz;
    double t7 = t4 * VVAR;
    double t8 = t3 + t3;
    double t9 = t8 * VAR(m_28);
    double t10 = fabs(t4 * (1.0 - t9) + t9);
    double t11 = exp(VAR(sshape_distortion) * log(t10)) * VVAR;
    double t12 = t10 * VVAR;
    double t13 = exp(VAR(sshape_roundwidth) * log(t8)) * VAR(m_28);
    double t14 = fabs(t4 * (1.0 - t13) + t13);
    double t15 = exp(VAR(sshape_distortion) * log(t14)) * VVAR;
    double t16 = t14 * VVAR;
    double t17 = atan2(t3 * VAR(m_30), 1.0) / VAR(m_20);
    double t18 = VAR(m_20) * ((double)(int)t1 + 1.0 - t17) - M_PI;
    double t19 = sqrt(FTx * FTx + FTy * FTy);
    double t20 = t19 * (1.0 / cos(t17 * VAR(m_20)));
    double t21 = 1.0 / cos(VAR(m_20) * t2);
    double t22 = t2 + t2;
    double t23 = t22 * VAR(m_28);
    double t24 = fabs(t21 * (1.0 - t23) + t23);
    double t25 = exp(VAR(sshape_distortion) * log(t24)) * VVAR;
    double t26 = t24 * VVAR;
    double t27 = exp(VAR(sshape_roundwidth) * log(t22)) * VAR(m_28);
    double t28 = fabs(t21 * (1.0 - t27) + t27);
    double t29 = exp(VAR(sshape_distortion) * log(t28)) * VVAR;
    double t30 = t28 * VVAR;
    double t31 = exp(VAR(sshape_distortion) * log(t21)) * VVAR;
    double t32 = t21 * VVAR;
    double t33 = atan2(t2 * VAR(m_30), 1.0) / VAR(m_20);
    double t34 = VAR(m_20) * ((double)(int)t1 + t33) - M_PI;
    double t35 = t19 * (1.0 / cos(t33 * VAR(m_20)));
    if (!(t2 > 0.5)) {
        if (VAR(sshape_compensation) != 0) {
            FPx = cos(t34) * t35 + FPx;
            FPy = t35 * sin(t34) + FPy;
            FPz = t6;
        } else {
            if (!(0.0 != VAR(sshape_roundstr))) {
                if (!(VAR(sshape_distortion) != 1.0)) {
                    FPx = FTx * t32 + FPx;
                    FPy = t32 * FTy + FPy;
                    FPz = t6;
                } else {
                    FPx = FTx * t31 + FPx;
                    FPy = t31 * FTy + FPy;
                    FPz = t6;
                }
            } else {
                if (VAR(sshape_roundwidth) != 1.0) {
                    if (!(VAR(sshape_distortion) != 1.0)) {
                        FPx = FTx * t30 + FPx;
                        FPy = t30 * FTy + FPy;
                        FPz = t6;
                    } else {
                        FPx = FTx * t29 + FPx;
                        FPy = t29 * FTy + FPy;
                        FPz = t6;
                    }
                } else {
                    if (!(VAR(sshape_distortion) != 1.0)) {
                        FPx = FTx * t26 + FPx;
                        FPy = t26 * FTy + FPy;
                        FPz = t6;
                    } else {
                        FPx = FTx * t25 + FPx;
                        FPy = t25 * FTy + FPy;
                        FPz = t6;
                    }
                }
            }
        }
    } else {
        if (VAR(sshape_compensation) != 0) {
            FPx = cos(t18) * t20 + FPx;
            FPy = t20 * sin(t18) + FPy;
            FPz = t6;
        } else {
            if (0.0 != VAR(sshape_roundstr)) {
                if (VAR(sshape_roundwidth) != 1.0) {
                    if (!(VAR(sshape_distortion) != 1.0)) {
                        FPx = FTx * t16 + FPx;
                        FPy = t16 * FTy + FPy;
                        FPz = t6;
                    } else {
                        FPx = FTx * t15 + FPx;
                        FPy = t15 * FTy + FPy;
                        FPz = t6;
                    }
                } else {
                    if (!(VAR(sshape_distortion) != 1.0)) {
                        FPx = FTx * t12 + FPx;
                        FPy = t12 * FTy + FPy;
                        FPz = t6;
                    } else {
                        FPx = FTx * t11 + FPx;
                        FPy = t11 * FTy + FPy;
                        FPz = t6;
                    }
                }
            } else {
                if (!(VAR(sshape_distortion) != 1.0)) {
                    FPx = FTx * t7 + FPx;
                    FPy = t7 * FTy + FPy;
                    FPz = t6;
                } else {
                    FPx = FTx * t5 + FPx;
                    FPy = t5 * FTy + FPy;
                    FPz = t6;
                }
            }
        }
    }
    return TRUE;
}