/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        cropn.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from cropn.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double cropn_power;
    double cropn_radius;
    double cropn_scatterdist;
    int cropn_zero;
    double m_18;
    double m_20;
    int m_28;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("cropn");
APO_VARIABLES(
    VAR_REAL(cropn_power, -5.0),
    VAR_REAL(cropn_radius, 1.0),
    VAR_REAL(cropn_scatterdist, 0.0),
    VAR_INTEGER_NONZERO(cropn_zero, 0)
);

int PluginVarPrepare(Variation* vp)
{
    double t1 = M_2PI / VAR(cropn_power);
    if ((int)(int)(VAR(cropn_power) > 0.0) != 0) {
        if (VAR(cropn_power) > 2.0) {
            VAR(m_28) = (int)(int)(VAR(cropn_power) > 0.0);
            VAR(m_18) = VAR(cropn_power);
            VAR(m_20) = t1;
        } else {
            VAR(m_28) = (int)(int)(VAR(cropn_power) > 0.0);
            VAR(m_18) = 2.0;
            VAR(m_20) = M_PI;
        }
    } else {
        if (VAR(cropn_power) > 2.0) {
            VAR(m_28) = (int)(int)(VAR(cropn_power) > 0.0);
            VAR(m_18) = VAR(cropn_power);
            VAR(m_20) = t1;
        } else {
            VAR(m_28) = (int)(int)(VAR(cropn_power) > 0.0);
            VAR(m_18) = 2.0;
            VAR(m_20) = M_PI;
        }
    }
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTz * VVAR + FPz;
    double t2 = atan2(FTy, FTx);
    double t3 = (t2 + M_PI) / VAR(m_20);
    double t4 = (t3 - (double)(int)t3) * VAR(m_20);
    double t5 = cos(VAR(m_20) - t4);
    double t6 = sqrt(FTx * FTx + FTy * FTy);
    double t7 = FTx * VVAR + FPx;
    double t8 = FTy * VVAR + FPy;
    double t9 = 0.5 * random01() * VAR(cropn_scatterdist);
    double t10 = VVAR * (t9 + 1.0);
    double t11 = cos(t2);
    double t12 = t10 * t11 + FPx;
    double t13 = sin(t2);
    double t14 = t10 * t13 + FPy;
    double t15 = VAR(cropn_radius) / t5;
    double t16 = VVAR * (t9 + t15);
    double t17 = t16 * t11 + FPx;
    double t18 = t16 * t13 + FPy;
    double t19 = cos(t4);
    double t20 = VAR(cropn_radius) / t19;
    double t21 = VVAR * (t9 + t20);
    double t22 = t21 * t11 + FPx;
    double t23 = t21 * t13 + FPy;
    if (VAR(m_20) / 2.0 > t4) {
        if (t19 > 0.0) {
            if (t6 > t20) {
                if (VAR(cropn_zero) == 0) {
                    if (1.0 != (double)VAR(m_28)) {
                        FPz = t1;
                        FPx = t7;
                        FPy = t8;
                    } else {
                        FPz = t1;
                        FPx = t22;
                        FPy = t23;
                    }
                } else {
                    if (1.0 != (double)VAR(m_28)) {
                        FPz = t1;
                        FPx = t7;
                        FPy = t8;
                    } else {
                        FPz = t1;
                        FPy = 0.0;
                        FPx = 0.0;
                    }
                }
            } else {
                if (VAR(cropn_zero) == 0) {
                    if (0.0 != (double)VAR(m_28)) {
                        FPz = t1;
                        FPx = t7;
                        FPy = t8;
                    } else {
                        FPz = t1;
                        FPx = t22;
                        FPy = t23;
                    }
                } else {
                    if (0.0 != (double)VAR(m_28)) {
                        FPz = t1;
                        FPx = t7;
                        FPy = t8;
                    } else {
                        FPz = t1;
                        FPy = 0.0;
                        FPx = 0.0;
                    }
                }
            }
        } else {
            if (t6 > 1.0) {
                if (VAR(cropn_zero) == 0) {
                    if (1.0 != (double)VAR(m_28)) {
                        FPz = t1;
                        FPx = t7;
                        FPy = t8;
                    } else {
                        FPz = t1;
                        FPx = t12;
                        FPy = t14;
                    }
                } else {
                    if (1.0 != (double)VAR(m_28)) {
                        FPz = t1;
                        FPx = t7;
                        FPy = t8;
                    } else {
                        FPz = t1;
                        FPy = 0.0;
                        FPx = 0.0;
                    }
                }
            } else {
                if (VAR(cropn_zero) == 0) {
                    if (0.0 != (double)VAR(m_28)) {
                        FPz = t1;
                        FPx = t7;
                        FPy = t8;
                    } else {
                        FPz = t1;
                        FPx = t12;
                        FPy = t14;
                    }
                } else {
                    if (0.0 != (double)VAR(m_28)) {
                        FPz = t1;
                        FPx = t7;
                        FPy = t8;
                    } else {
                        FPz = t1;
                        FPy = 0.0;
                        FPx = 0.0;
                    }
                }
            }
        }
    } else {
        if (t5 > 0.0) {
            if (t6 > t15) {
                if (VAR(cropn_zero) == 0) {
                    if (1.0 != (double)VAR(m_28)) {
                        FPz = t1;
                        FPx = t7;
                        FPy = t8;
                    } else {
                        FPz = t1;
                        FPx = t17;
                        FPy = t18;
                    }
                } else {
                    if (1.0 != (double)VAR(m_28)) {
                        FPz = t1;
                        FPx = t7;
                        FPy = t8;
                    } else {
                        FPz = t1;
                        FPy = 0.0;
                        FPx = 0.0;
                    }
                }
            } else {
                if (VAR(cropn_zero) == 0) {
                    if (0.0 != (double)VAR(m_28)) {
                        FPz = t1;
                        FPx = t7;
                        FPy = t8;
                    } else {
                        FPz = t1;
                        FPx = t17;
                        FPy = t18;
                    }
                } else {
                    if (0.0 != (double)VAR(m_28)) {
                        FPz = t1;
                        FPx = t7;
                        FPy = t8;
                    } else {
                        FPz = t1;
                        FPy = 0.0;
                        FPx = 0.0;
                    }
                }
            }
        } else {
            if (t6 > 1.0) {
                if (VAR(cropn_zero) == 0) {
                    if (1.0 != (double)VAR(m_28)) {
                        FPz = t1;
                        FPx = t7;
                        FPy = t8;
                    } else {
                        FPz = t1;
                        FPx = t12;
                        FPy = t14;
                    }
                } else {
                    if (1.0 != (double)VAR(m_28)) {
                        FPz = t1;
                        FPx = t7;
                        FPy = t8;
                    } else {
                        FPz = t1;
                        FPy = 0.0;
                        FPx = 0.0;
                    }
                }
            } else {
                if (VAR(cropn_zero) == 0) {
                    if (0.0 != (double)VAR(m_28)) {
                        FPz = t1;
                        FPx = t7;
                        FPy = t8;
                    } else {
                        FPz = t1;
                        FPx = t12;
                        FPy = t14;
                    }
                } else {
                    if (0.0 != (double)VAR(m_28)) {
                        FPz = t1;
                        FPx = t7;
                        FPy = t8;
                    } else {
                        FPz = t1;
                        FPy = 0.0;
                        FPx = 0.0;
                    }
                }
            }
        }
    }
    return TRUE;
}