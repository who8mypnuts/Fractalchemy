/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        post_smartshape_beta_x86.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from post_smartshape_beta_x86.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double post_sshape_power;
    double post_sshape_roundstr;
    double post_sshape_roundwidth;
    double post_sshape_distortion;
    double m_20;
    double m_28;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("post_smartshape");
APO_VARIABLES(
    VAR_REAL(post_sshape_power, 4.0),
    VAR_REAL(post_sshape_roundstr, 0.0),
    VAR_REAL(post_sshape_roundwidth, 1.0),
    VAR_REAL(post_sshape_distortion, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    double t1 = VAR(post_sshape_roundstr) / 2.0;
    double t2 = M_2PI / VAR(post_sshape_power);
    double t3 = VAR(post_sshape_roundstr) / (VAR(post_sshape_power) * sin(0.5 * t2));
    if (VAR(post_sshape_power) >= 2.0) {
        VAR(m_20) = t2;
        VAR(m_28) = t3 + t3;
    } else {
        VAR(post_sshape_power) = 2.0;
        VAR(m_20) = M_PI;
        VAR(m_28) = t1 + t1;
    }
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = (atan2(FPy, FPx) + M_PI) / VAR(m_20);
    double t2 = t1 - (double)(int)t1;
    double t3 = 1.0 - t2;
    double t4 = 1.0 / cos(VAR(m_20) * t3);
    double t5 = t3 + t3;
    double t6 = t5 * VAR(m_28);
    double t7 = fabs(t4 * (1.0 - t6) + t6);
    double t8 = t7 * VVAR;
    double t9 = exp(VAR(post_sshape_distortion) * log(t7)) * VVAR;
    double t10 = exp(VAR(post_sshape_roundwidth) * log(t5)) * VAR(m_28);
    double t11 = fabs(t4 * (1.0 - t10) + t10);
    double t12 = t11 * VVAR;
    double t13 = exp(VAR(post_sshape_distortion) * log(t11)) * VVAR;
    double t14 = t4 * VVAR;
    double t15 = exp(VAR(post_sshape_distortion) * log(t4)) * VVAR;
    double t16 = 1.0 / cos(VAR(m_20) * t2);
    double t17 = t2 + t2;
    double t18 = t17 * VAR(m_28);
    double t19 = fabs(t16 * (1.0 - t18) + t18);
    double t20 = t19 * VVAR;
    double t21 = exp(VAR(post_sshape_distortion) * log(t19)) * VVAR;
    double t22 = exp(VAR(post_sshape_roundwidth) * log(t17)) * VAR(m_28);
    double t23 = fabs(t16 * (1.0 - t22) + t22);
    double t24 = t23 * VVAR;
    double t25 = exp(VAR(post_sshape_distortion) * log(t23)) * VVAR;
    double t26 = t16 * VVAR;
    double t27 = exp(VAR(post_sshape_distortion) * log(t16)) * VVAR;
    if (!(VAR(post_sshape_distortion) != 0.0)) {
        FPx = FPx * VVAR;
        FPy = FPy * VVAR;
        FPz = VVAR * FPz;
    } else {
        if (!(t2 >= 0.5)) {
            if (!(0.0 != VAR(post_sshape_roundstr))) {
                if (VAR(post_sshape_distortion) != 1.0) {
                    FPx = FPx * t27;
                    FPy = FPy * t27;
                    FPz = t27 * FPz;
                } else {
                    FPx = FPx * t26;
                    FPy = FPy * t26;
                    FPz = t26 * FPz;
                }
            } else {
                if (VAR(post_sshape_roundwidth) != 1.0) {
                    if (VAR(post_sshape_distortion) != 1.0) {
                        FPx = FPx * t25;
                        FPy = FPy * t25;
                        FPz = t25 * FPz;
                    } else {
                        FPx = FPx * t24;
                        FPy = FPy * t24;
                        FPz = t24 * FPz;
                    }
                } else {
                    if (VAR(post_sshape_distortion) != 1.0) {
                        FPx = FPx * t21;
                        FPy = FPy * t21;
                        FPz = t21 * FPz;
                    } else {
                        FPx = FPx * t20;
                        FPy = FPy * t20;
                        FPz = t20 * FPz;
                    }
                }
            }
        } else {
            if (!(0.0 != VAR(post_sshape_roundstr))) {
                if (VAR(post_sshape_distortion) != 1.0) {
                    FPx = FPx * t15;
                    FPy = FPy * t15;
                    FPz = t15 * FPz;
                } else {
                    FPx = FPx * t14;
                    FPy = FPy * t14;
                    FPz = t14 * FPz;
                }
            } else {
                if (VAR(post_sshape_roundwidth) != 1.0) {
                    if (VAR(post_sshape_distortion) != 1.0) {
                        FPx = FPx * t13;
                        FPy = FPy * t13;
                        FPz = t13 * FPz;
                    } else {
                        FPx = FPx * t12;
                        FPy = FPy * t12;
                        FPz = t12 * FPz;
                    }
                } else {
                    if (VAR(post_sshape_distortion) != 1.0) {
                        FPx = FPx * t9;
                        FPy = FPy * t9;
                        FPz = t9 * FPz;
                    } else {
                        FPx = FPx * t8;
                        FPy = FPy * t8;
                        FPz = t8 * FPz;
                    }
                }
            }
        }
    }
    return TRUE;
}