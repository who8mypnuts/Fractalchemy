/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        waves2b.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from waves2b.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz', 32: 'TC'} var_base=88

typedef struct {
    double waves2b_freqx;
    double waves2b_freqy;
    double waves2b_pwx;
    double waves2b_pwy;
    double waves2b_scalex;
    double waves2b_scaleinfx;
    double waves2b_scaley;
    double waves2b_scaleinfy;
    double waves2b_unity;
    double m_40;
    double m_48;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("waves2b");
APO_VARIABLES(
    VAR_REAL(waves2b_freqx, 2.0),
    VAR_REAL(waves2b_freqy, 2.0),
    VAR_REAL(waves2b_pwx, 1.0),
    VAR_REAL(waves2b_pwy, 1.0),
    VAR_REAL(waves2b_scalex, 1.0),
    VAR_REAL(waves2b_scaleinfx, 1.0),
    VAR_REAL(waves2b_scaley, 1.0),
    VAR_REAL(waves2b_scaleinfy, 1.0),
    VAR_REAL(waves2b_unity, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_40) = VAR(waves2b_scalex) - VAR(waves2b_scaleinfx);
    VAR(m_48) = VAR(waves2b_scaley) - VAR(waves2b_scaleinfy);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTx * FTx + VAR(waves2b_unity);
    double t2 = FTy * FTy + VAR(waves2b_unity);
    double t3 = pow(fabs(FTy) + 1e-10, VAR(waves2b_pwx));
    double t4 = sin(t3 * VAR(waves2b_freqx));
    double t5 = VAR(m_40) * (VAR(waves2b_unity) / t1) + VAR(waves2b_scaleinfx);
    double t6 = (t4 * t5 + FTx) * VVAR + FPx;
    double t7 = pow(fabs(FTx) + 1e-10, VAR(waves2b_pwy));
    double t8 = sin(t7 * VAR(waves2b_freqy));
    double t9 = VAR(m_48) * (VAR(waves2b_unity) / t2) + VAR(waves2b_scaleinfy);
    double t10 = (t8 * t9 + FTy) * VVAR + FPy;
    double t11 = sin(-t7 * VAR(waves2b_freqy));
    double t12 = (t11 * t9 + FTy) * VVAR + FPy;
    double t13 = sin(-t3 * VAR(waves2b_freqx));
    double t14 = (t13 * t5 + FTx) * VVAR + FPx;
    double t15 = VAR(m_48) * (1.0 / t2) + VAR(waves2b_scaleinfy);
    double t16 = (t8 * t15 + FTy) * VVAR + FPy;
    double t17 = (t11 * t15 + FTy) * VVAR + FPy;
    double t18 = VAR(m_40) * (1.0 / t1) + VAR(waves2b_scaleinfx);
    double t19 = (t4 * t18 + FTx) * VVAR + FPx;
    double t20 = (t13 * t18 + FTx) * VVAR + FPx;
    if (1e-10 > t1) {
        if (1e-10 > t2) {
            if (0.0 > FTy) {
                if (0.0 > FTx) {
                    FPx = t20;
                    FPy = t17;
                } else {
                    FPx = t20;
                    FPy = t16;
                }
            } else {
                if (0.0 > FTx) {
                    FPx = t19;
                    FPy = t17;
                } else {
                    FPx = t19;
                    FPy = t16;
                }
            }
        } else {
            if (0.0 > FTy) {
                if (0.0 > FTx) {
                    FPx = t20;
                    FPy = t12;
                } else {
                    FPx = t20;
                    FPy = t10;
                }
            } else {
                if (0.0 > FTx) {
                    FPx = t19;
                    FPy = t12;
                } else {
                    FPx = t19;
                    FPy = t10;
                }
            }
        }
    } else {
        if (1e-10 > t2) {
            if (0.0 > FTy) {
                if (0.0 > FTx) {
                    FPx = t14;
                    FPy = t17;
                } else {
                    FPx = t14;
                    FPy = t16;
                }
            } else {
                if (0.0 > FTx) {
                    FPx = t6;
                    FPy = t17;
                } else {
                    FPx = t6;
                    FPy = t16;
                }
            }
        } else {
            if (0.0 > FTy) {
                if (0.0 > FTx) {
                    FPx = t14;
                    FPy = t12;
                } else {
                    FPx = t14;
                    FPy = t10;
                }
            } else {
                if (0.0 > FTx) {
                    FPx = t6;
                    FPy = t12;
                } else {
                    FPx = t6;
                    FPy = t10;
                }
            }
        }
    }
    return TRUE;
}