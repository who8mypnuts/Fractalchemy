/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        supershape.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from supershape.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double super_shape_m;
    double super_shape_n1;
    double super_shape_n2;
    double super_shape_n3;
    double super_shape_rnd;
    double super_shape_holes;
    double m_30;
    double m_38;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("super_shape");
APO_VARIABLES(
    VAR_REAL(super_shape_m, 5.0),
    VAR_REAL(super_shape_n1, 2.0),
    VAR_REAL(super_shape_n2, 0.3),
    VAR_REAL(super_shape_n3, 0.3),
    VAR_REAL(super_shape_rnd, 0.0),
    VAR_REAL(super_shape_holes, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_30) = 1.0 - VAR(super_shape_rnd);
    VAR(m_38) = -1.0 / VAR(super_shape_n1);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = isnan(VAR(super_shape_n1));
    double t2 = isnan(0.0);
    double t3 = 0.0 * VVAR;
    double t4 = cos(0.0) * t3 + FPx;
    double t5 = sin(0.0) * t3 + FPy;
    double t6 = sqrt(FTx * FTx + FTy * FTy);
    double t7 = isnan(t6 + t6);
    double t8 = random01() * VAR(super_shape_rnd);
    double t9 = atan2(FTy, FTx);
    double t10 = 0.25 * (t9 * VAR(super_shape_m) + M_PI);
    double t11 = pow(pow(fabs(cos(t10)), VAR(super_shape_n2)) + pow(sin(t10), VAR(super_shape_n3)), VAR(m_38));
    double t12 = (t6 * VAR(m_30) + t8 - VAR(super_shape_holes)) * t11;
    double t13 = isnan(t12);
    double t14 = cos(t9);
    double t15 = t14 * (VVAR * t12) + FPx;
    double t16 = sin(t9);
    double t17 = t16 * (t12 * VVAR) + FPy;
    double t18 = (0.0 * VAR(m_30) + t8 - VAR(super_shape_holes)) * t11;
    double t19 = isnan(t18);
    double t20 = t14 * (VVAR * t18) + FPx;
    double t21 = t16 * (t18 * VVAR) + FPy;
    if (t1) {
        if (1.0 <= VAR(super_shape_rnd)) {
            if (t19) {
                FPx = t20;
                FPy = t21;
            } else {
                if (t18 == 0.0) {
                } else {
                    FPx = t20;
                    FPy = t21;
                }
            }
        } else {
            if (t7) {
                if (t13) {
                    FPx = t15;
                    FPy = t17;
                } else {
                    if (t12 == 0.0) {
                    } else {
                        FPx = t15;
                        FPy = t17;
                    }
                }
            } else {
                if (t6 != t6) {
                    if (t13) {
                        FPx = t15;
                        FPy = t17;
                    } else {
                        if (t12 == 0.0) {
                        } else {
                            FPx = t15;
                            FPy = t17;
                        }
                    }
                } else {
                    if (t13) {
                        FPx = t15;
                        FPy = t17;
                    } else {
                        if (t12 == 0.0) {
                        } else {
                            FPx = t15;
                            FPy = t17;
                        }
                    }
                }
            }
        }
    } else {
        if (VAR(super_shape_n1) != 0.0) {
            if (1.0 <= VAR(super_shape_rnd)) {
                if (t19) {
                    FPx = t20;
                    FPy = t21;
                } else {
                    if (t18 == 0.0) {
                    } else {
                        FPx = t20;
                        FPy = t21;
                    }
                }
            } else {
                if (t7) {
                    if (t13) {
                        FPx = t15;
                        FPy = t17;
                    } else {
                        if (t12 == 0.0) {
                        } else {
                            FPx = t15;
                            FPy = t17;
                        }
                    }
                } else {
                    if (t6 != t6) {
                        if (t13) {
                            FPx = t15;
                            FPy = t17;
                        } else {
                            if (t12 == 0.0) {
                            } else {
                                FPx = t15;
                                FPy = t17;
                            }
                        }
                    } else {
                        if (t13) {
                            FPx = t15;
                            FPy = t17;
                        } else {
                            if (t12 == 0.0) {
                            } else {
                                FPx = t15;
                                FPy = t17;
                            }
                        }
                    }
                }
            }
        } else {
            if (t2) {
                FPx = t4;
                FPy = t5;
            } else {
                if (0.0 == 0.0) {
                } else {
                    FPx = t4;
                    FPy = t5;
                }
            }
        }
    }
    return TRUE;
}