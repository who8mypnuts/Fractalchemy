/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        cubicLattice_3D.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from cubicLattice_3D.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double cubic3D_xpand;
    double cubic3D_style;
    double m_10;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("cubicLattice_3D");
APO_VARIABLES(
    VAR_REAL(cubic3D_xpand, 0.2),
    VAR_REAL(cubic3D_style, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_10) = (int)(int)(fabs(VAR(cubic3D_style)) >= 2.0) + 1;
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTx + FPx;
    double t2 = 0.5 * VAR(cubic3D_xpand);
    double t3 = t1 * t2;
    double t4 = t3 + VVAR;
    double t5 = FTy + FPy;
    double t6 = t5 * t2;
    double t7 = t6 + VVAR;
    double t8 = FTz + FPz;
    double t9 = t2 * t8;
    double t10 = VVAR + t9;
    double t11 = t3 - VVAR;
    double t12 = t6 - VVAR;
    double t13 = t9 - VVAR;
    double t14 = cos(atan2(FTx, FTz));
    double t15 = t14 * t3;
    double t16 = t15 + VVAR;
    double t17 = sin(atan2(FTy, FTz));
    double t18 = t17 * t6;
    double t19 = t18 + VVAR;
    double t20 = 0.5 * (t14 + t17);
    double t21 = t9 * t20;
    double t22 = VVAR + t21;
    double t23 = t15 - VVAR;
    double t24 = t18 - VVAR;
    double t25 = t21 - VVAR;
    double t26 = 0.5 * sqrt(VAR(cubic3D_xpand));
    double t27 = t1 * t26;
    double t28 = t14 * t27;
    double t29 = t28 + VVAR;
    double t30 = t5 * t26;
    double t31 = t17 * t30;
    double t32 = t31 + VVAR;
    double t33 = t26 * t8;
    double t34 = t33 * t20;
    double t35 = VVAR + t34;
    double t36 = t28 - VVAR;
    double t37 = t31 - VVAR;
    double t38 = t34 - VVAR;
    double t39 = t27 + VVAR;
    double t40 = t30 + VVAR;
    double t41 = VVAR + t33;
    double t42 = t27 - VVAR;
    double t43 = t30 - VVAR;
    double t44 = t33 - VVAR;
    if (fabs(VAR(cubic3D_xpand)) > 1.0) {
        if (VAR(m_10) != 2) {
            if ((int)trunc(8.0 * random01()) != 0) {
                if ((int)trunc(8.0 * random01()) == 1) {
                    FPx = t39;
                    FPy = t43;
                    FPz = t41;
                } else {
                    if ((int)trunc(8.0 * random01()) == 2) {
                        FPx = t39;
                        FPy = t40;
                        FPz = t44;
                    } else {
                        if ((int)trunc(8.0 * random01()) == 3) {
                            FPx = t39;
                            FPy = t43;
                            FPz = t44;
                        } else {
                            if ((int)trunc(8.0 * random01()) == 4) {
                                FPx = t42;
                                FPy = t40;
                                FPz = t41;
                            } else {
                                if ((int)trunc(8.0 * random01()) == 5) {
                                    FPx = t42;
                                    FPy = t43;
                                    FPz = t41;
                                } else {
                                    if ((int)trunc(8.0 * random01()) == 6) {
                                        FPx = t42;
                                        FPy = t40;
                                        FPz = t44;
                                    } else {
                                        if ((int)trunc(8.0 * random01()) != 7) {
                                        } else {
                                            FPx = t42;
                                            FPy = t43;
                                            FPz = t44;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            } else {
                FPx = t39;
                FPy = t40;
                FPz = t41;
            }
        } else {
            if ((int)trunc(8.0 * random01()) != 0) {
                if ((int)trunc(8.0 * random01()) == 1) {
                    FPx = t29;
                    FPy = t37;
                    FPz = t35;
                } else {
                    if ((int)trunc(8.0 * random01()) == 2) {
                        FPx = t29;
                        FPy = t32;
                        FPz = t38;
                    } else {
                        if ((int)trunc(8.0 * random01()) == 3) {
                            FPx = t29;
                            FPy = t37;
                            FPz = t38;
                        } else {
                            if ((int)trunc(8.0 * random01()) == 4) {
                                FPx = t36;
                                FPy = t32;
                                FPz = t35;
                            } else {
                                if ((int)trunc(8.0 * random01()) == 5) {
                                    FPx = t36;
                                    FPy = t37;
                                    FPz = t35;
                                } else {
                                    if ((int)trunc(8.0 * random01()) == 6) {
                                        FPx = t36;
                                        FPy = t32;
                                        FPz = t38;
                                    } else {
                                        if ((int)trunc(8.0 * random01()) != 7) {
                                        } else {
                                            FPx = t36;
                                            FPy = t37;
                                            FPz = t38;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            } else {
                FPx = t29;
                FPy = t32;
                FPz = t35;
            }
        }
    } else {
        if (VAR(m_10) == 2) {
            if ((int)trunc(8.0 * random01()) != 0) {
                if ((int)trunc(8.0 * random01()) == 1) {
                    FPx = t16;
                    FPy = t24;
                    FPz = t22;
                } else {
                    if ((int)trunc(8.0 * random01()) == 2) {
                        FPx = t16;
                        FPy = t19;
                        FPz = t25;
                    } else {
                        if ((int)trunc(8.0 * random01()) == 3) {
                            FPx = t16;
                            FPy = t24;
                            FPz = t25;
                        } else {
                            if ((int)trunc(8.0 * random01()) == 4) {
                                FPx = t23;
                                FPy = t19;
                                FPz = t22;
                            } else {
                                if ((int)trunc(8.0 * random01()) == 5) {
                                    FPx = t23;
                                    FPy = t24;
                                    FPz = t22;
                                } else {
                                    if ((int)trunc(8.0 * random01()) == 6) {
                                        FPx = t23;
                                        FPy = t19;
                                        FPz = t25;
                                    } else {
                                        if ((int)trunc(8.0 * random01()) != 7) {
                                        } else {
                                            FPx = t23;
                                            FPy = t24;
                                            FPz = t25;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            } else {
                FPx = t16;
                FPy = t19;
                FPz = t22;
            }
        } else {
            if ((int)trunc(8.0 * random01()) != 0) {
                if ((int)trunc(8.0 * random01()) == 1) {
                    FPx = t4;
                    FPy = t12;
                    FPz = t10;
                } else {
                    if ((int)trunc(8.0 * random01()) == 2) {
                        FPx = t4;
                        FPy = t7;
                        FPz = t13;
                    } else {
                        if ((int)trunc(8.0 * random01()) == 3) {
                            FPx = t4;
                            FPy = t12;
                            FPz = t13;
                        } else {
                            if ((int)trunc(8.0 * random01()) == 4) {
                                FPx = t11;
                                FPy = t7;
                                FPz = t10;
                            } else {
                                if ((int)trunc(8.0 * random01()) == 5) {
                                    FPx = t11;
                                    FPy = t12;
                                    FPz = t10;
                                } else {
                                    if ((int)trunc(8.0 * random01()) == 6) {
                                        FPx = t11;
                                        FPy = t7;
                                        FPz = t13;
                                    } else {
                                        if ((int)trunc(8.0 * random01()) != 7) {
                                        } else {
                                            FPx = t11;
                                            FPy = t12;
                                            FPz = t13;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            } else {
                FPx = t4;
                FPy = t7;
                FPz = t10;
            }
        }
    }
    return TRUE;
}