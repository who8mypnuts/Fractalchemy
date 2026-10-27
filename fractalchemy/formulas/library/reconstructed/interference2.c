/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        interference2.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from interference2.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double intrfr2_a1;
    double intrfr2_b1;
    double intrfr2_c1;
    double intrfr2_p1;
    int intrfr2_t1;
    double intrfr2_a2;
    double intrfr2_b2;
    double intrfr2_c2;
    double intrfr2_p2;
    int intrfr2_t2;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("interference2");
APO_VARIABLES(
    VAR_REAL(intrfr2_a1, 1.0),
    VAR_REAL(intrfr2_b1, 1.0),
    VAR_REAL(intrfr2_c1, 0.0),
    VAR_REAL(intrfr2_p1, 1.0),
    VAR_INTEGER(intrfr2_t1, 0),
    VAR_REAL(intrfr2_a2, 1.0),
    VAR_REAL(intrfr2_b2, 1.0),
    VAR_REAL(intrfr2_c2, 0.0),
    VAR_REAL(intrfr2_p2, 1.0),
    VAR_INTEGER(intrfr2_t2, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = VAR(intrfr2_b2) * FTx + VAR(intrfr2_c2);
    double t2 = VAR(intrfr2_a2) + VAR(intrfr2_a2);
    double t3 = pow(asin(cos(t1 - M_PI_2)) / M_PI, VAR(intrfr2_p2)) * t2;
    double t4 = VAR(intrfr2_b1) * FTx + VAR(intrfr2_c1);
    double t5 = VAR(intrfr2_a1) + VAR(intrfr2_a1);
    double t6 = pow(asin(cos(t4 - M_PI_2)) / M_PI, VAR(intrfr2_p1)) * t5;
    double t7 = (t3 + t6) * VVAR + FPx;
    double t8 = VAR(intrfr2_b2) * FTy + VAR(intrfr2_c2);
    double t9 = pow(asin(cos(t8 - M_PI_2)) / M_PI, VAR(intrfr2_p2)) * t2;
    double t10 = VAR(intrfr2_b1) * FTy + VAR(intrfr2_c1);
    double t11 = pow(asin(cos(t10 - M_PI_2)) / M_PI, VAR(intrfr2_p1)) * t5;
    double t12 = (t9 + t11) * VVAR + FPy;
    double t13 = sin(t8);
    double t14 = pow(1.0, VAR(intrfr2_p2)) * VAR(intrfr2_a2);
    double t15 = (t14 + t11) * VVAR + FPy;
    double t16 = pow(-1.0, VAR(intrfr2_p2)) * VAR(intrfr2_a2);
    double t17 = (t16 + t11) * VVAR + FPy;
    double t18 = pow(t13, VAR(intrfr2_p2)) * VAR(intrfr2_a2);
    double t19 = (t18 + t11) * VVAR + FPy;
    double t20 = sin(t10);
    double t21 = pow(1.0, VAR(intrfr2_p1)) * VAR(intrfr2_a1);
    double t22 = (t9 + t21) * VVAR + FPy;
    double t23 = (t14 + t21) * VVAR;
    double t24 = t23 + FPy;
    double t25 = (t16 + t21) * VVAR;
    double t26 = t25 + FPy;
    double t27 = (t18 + t21) * VVAR + FPy;
    double t28 = pow(-1.0, VAR(intrfr2_p1)) * VAR(intrfr2_a1);
    double t29 = (t9 + t28) * VVAR + FPy;
    double t30 = (t14 + t28) * VVAR;
    double t31 = t30 + FPy;
    double t32 = (t16 + t28) * VVAR;
    double t33 = t32 + FPy;
    double t34 = (t18 + t28) * VVAR + FPy;
    double t35 = pow(t20, VAR(intrfr2_p1)) * VAR(intrfr2_a1);
    double t36 = (t9 + t35) * VVAR + FPy;
    double t37 = (t14 + t35) * VVAR + FPy;
    double t38 = (t16 + t35) * VVAR + FPy;
    double t39 = (t18 + t35) * VVAR + FPy;
    double t40 = sin(t1);
    double t41 = (t14 + t6) * VVAR + FPx;
    double t42 = (t16 + t6) * VVAR + FPx;
    double t43 = pow(t40, VAR(intrfr2_p2)) * VAR(intrfr2_a2);
    double t44 = (t43 + t6) * VVAR + FPx;
    double t45 = sin(t4);
    double t46 = (t3 + t21) * VVAR + FPx;
    double t47 = t23 + FPx;
    double t48 = t25 + FPx;
    double t49 = (t43 + t21) * VVAR + FPx;
    double t50 = (t3 + t28) * VVAR + FPx;
    double t51 = t30 + FPx;
    double t52 = t32 + FPx;
    double t53 = (t43 + t28) * VVAR + FPx;
    double t54 = pow(t45, VAR(intrfr2_p1)) * VAR(intrfr2_a1);
    double t55 = (t3 + t54) * VVAR + FPx;
    double t56 = (t14 + t54) * VVAR + FPx;
    double t57 = (t16 + t54) * VVAR + FPx;
    double t58 = (t43 + t54) * VVAR + FPx;
    if (!(VAR(intrfr2_t1) == 1)) {
        if (!(VAR(intrfr2_t1) == 2)) {
            if (!(VAR(intrfr2_t2) == 1)) {
                if (!(VAR(intrfr2_t2) == 2)) {
                    FPx = t58;
                    FPy = t39;
                } else if (!(VAR(intrfr2_t2) == 2)) {
                    FPx = t58;
                    FPy = t36;
                } else if (!(VAR(intrfr2_t2) == 2)) {
                    if (!(VAR(intrfr2_t1) == 1)) {
                        FPx = t58;
                        FPy = t38;
                    } else {
                        FPx = t58;
                        FPy = t37;
                    }
                }
            } else if (!(VAR(intrfr2_t2) == 1)) {
                if (!(VAR(intrfr2_t2) == 2)) {
                    FPx = t58;
                    FPy = t19;
                } else if (!(VAR(intrfr2_t2) == 2)) {
                    FPx = t58;
                    FPy = t12;
                } else if (!(VAR(intrfr2_t2) == 2)) {
                    if (VAR(intrfr2_t1) == 1) {
                        FPx = t58;
                        FPy = t17;
                    } else {
                        FPx = t58;
                        FPy = t15;
                    }
                }
            } else if (!(VAR(intrfr2_t2) == 1)) {
                if (!(VAR(intrfr2_t2) == 2)) {
                    if (VAR(intrfr2_t1) == 2) {
                        FPx = t58;
                        FPy = t34;
                    } else if (VAR(intrfr2_t1) == 2) {
                        FPx = t58;
                        FPy = t29;
                    } else if (VAR(intrfr2_t1) == 2) {
                        if (!(VAR(intrfr2_t1) == 1)) {
                            FPx = t58;
                            FPy = t33;
                        } else {
                            FPx = t58;
                            FPy = t31;
                        }
                    }
                } else {
                    if (VAR(intrfr2_t1) == 2) {
                        FPx = t58;
                        FPy = t27;
                    } else if (VAR(intrfr2_t1) == 2) {
                        FPx = t58;
                        FPy = t22;
                    } else if (VAR(intrfr2_t1) == 2) {
                        if (!(VAR(intrfr2_t1) == 1)) {
                            FPx = t58;
                            FPy = t26;
                        } else {
                            FPx = t58;
                            FPy = t24;
                        }
                    }
                }
            }
        } else if (!(VAR(intrfr2_t1) == 2)) {
            if (VAR(intrfr2_t2) == 1) {
                if (!(VAR(intrfr2_t1) == 1)) {
                    FPx = t55;
                    FPy = t39;
                } else if (!(VAR(intrfr2_t1) == 1)) {
                    FPx = t55;
                    FPy = t36;
                } else if (!(VAR(intrfr2_t1) == 1)) {
                    if (!(VAR(intrfr2_t1) == 2)) {
                        FPx = t55;
                        FPy = t38;
                    } else {
                        FPx = t55;
                        FPy = t37;
                    }
                }
            } else if (VAR(intrfr2_t2) == 1) {
                if (VAR(intrfr2_t1) == 1) {
                    FPx = t55;
                    FPy = t19;
                } else if (VAR(intrfr2_t1) == 1) {
                    FPx = t55;
                    FPy = t12;
                } else if (VAR(intrfr2_t1) == 1) {
                    if (VAR(intrfr2_t2) == 2) {
                        FPx = t55;
                        FPy = t17;
                    } else {
                        FPx = t55;
                        FPy = t15;
                    }
                }
            } else if (VAR(intrfr2_t2) == 1) {
                if (VAR(intrfr2_t1) == 2) {
                    if (!(VAR(intrfr2_t1) == 1)) {
                        FPx = t55;
                        FPy = t34;
                    } else if (!(VAR(intrfr2_t1) == 1)) {
                        FPx = t55;
                        FPy = t29;
                    } else if (!(VAR(intrfr2_t1) == 1)) {
                        if (0.0 > t20) {
                            FPx = t55;
                            FPy = t33;
                        } else {
                            FPx = t55;
                            FPy = t31;
                        }
                    }
                } else {
                    if (!(VAR(intrfr2_t1) == 1)) {
                        FPx = t55;
                        FPy = t27;
                    } else if (!(VAR(intrfr2_t1) == 1)) {
                        FPx = t55;
                        FPy = t22;
                    } else if (!(VAR(intrfr2_t1) == 1)) {
                        if (!(0.0 > t20)) {
                            FPx = t55;
                            FPy = t26;
                        } else {
                            FPx = t55;
                            FPy = t24;
                        }
                    }
                }
            }
        } else if (!(VAR(intrfr2_t1) == 2)) {
            if (VAR(intrfr2_t2) == 2) {
                if (!(VAR(intrfr2_t2) == 1)) {
                    if (0.0 > t40) {
                        FPx = t57;
                        FPy = t39;
                    } else if (0.0 > t40) {
                        FPx = t57;
                        FPy = t36;
                    } else if (0.0 > t40) {
                        if (!(VAR(intrfr2_t1) == 1)) {
                            FPx = t57;
                            FPy = t38;
                        } else {
                            FPx = t57;
                            FPy = t37;
                        }
                    }
                } else if (!(VAR(intrfr2_t2) == 1)) {
                    if (0.0 > t40) {
                        FPx = t57;
                        FPy = t19;
                    } else if (0.0 > t40) {
                        FPx = t57;
                        FPy = t12;
                    } else if (0.0 > t40) {
                        if (VAR(intrfr2_t1) == 1) {
                            FPx = t57;
                            FPy = t17;
                        } else {
                            FPx = t57;
                            FPy = t15;
                        }
                    }
                } else if (!(VAR(intrfr2_t2) == 1)) {
                    if (0.0 > t40) {
                        if (VAR(intrfr2_t1) == 2) {
                            FPx = t57;
                            FPy = t34;
                        } else if (VAR(intrfr2_t1) == 2) {
                            FPx = t57;
                            FPy = t29;
                        } else if (VAR(intrfr2_t1) == 2) {
                            if (!(VAR(intrfr2_t1) == 1)) {
                                FPx = t57;
                                FPy = t33;
                            } else {
                                FPx = t57;
                                FPy = t31;
                            }
                        }
                    } else {
                        if (VAR(intrfr2_t1) == 2) {
                            FPx = t57;
                            FPy = t27;
                        } else if (VAR(intrfr2_t1) == 2) {
                            FPx = t57;
                            FPy = t22;
                        } else if (VAR(intrfr2_t1) == 2) {
                            if (!(VAR(intrfr2_t1) == 1)) {
                                FPx = t57;
                                FPy = t26;
                            } else {
                                FPx = t57;
                                FPy = t24;
                            }
                        }
                    }
                }
            } else {
                if (!(VAR(intrfr2_t2) == 1)) {
                    if (!(0.0 > t40)) {
                        FPx = t56;
                        FPy = t39;
                    } else if (!(0.0 > t40)) {
                        FPx = t56;
                        FPy = t36;
                    } else if (!(0.0 > t40)) {
                        if (!(VAR(intrfr2_t1) == 1)) {
                            FPx = t56;
                            FPy = t38;
                        } else {
                            FPx = t56;
                            FPy = t37;
                        }
                    }
                } else if (!(VAR(intrfr2_t2) == 1)) {
                    if (!(0.0 > t40)) {
                        FPx = t56;
                        FPy = t19;
                    } else if (!(0.0 > t40)) {
                        FPx = t56;
                        FPy = t12;
                    } else if (!(0.0 > t40)) {
                        if (VAR(intrfr2_t1) == 1) {
                            FPx = t56;
                            FPy = t17;
                        } else {
                            FPx = t56;
                            FPy = t15;
                        }
                    }
                } else if (!(VAR(intrfr2_t2) == 1)) {
                    if (!(0.0 > t40)) {
                        if (VAR(intrfr2_t1) == 2) {
                            FPx = t56;
                            FPy = t34;
                        } else if (VAR(intrfr2_t1) == 2) {
                            FPx = t56;
                            FPy = t29;
                        } else if (VAR(intrfr2_t1) == 2) {
                            if (!(VAR(intrfr2_t1) == 1)) {
                                FPx = t56;
                                FPy = t33;
                            } else {
                                FPx = t56;
                                FPy = t31;
                            }
                        }
                    } else {
                        if (VAR(intrfr2_t1) == 2) {
                            FPx = t56;
                            FPy = t27;
                        } else if (VAR(intrfr2_t1) == 2) {
                            FPx = t56;
                            FPy = t22;
                        } else if (VAR(intrfr2_t1) == 2) {
                            if (!(VAR(intrfr2_t1) == 1)) {
                                FPx = t56;
                                FPy = t26;
                            } else {
                                FPx = t56;
                                FPy = t24;
                            }
                        }
                    }
                }
            }
        }
    } else if (VAR(intrfr2_t1) == 1) {
        if (!(VAR(intrfr2_t2) == 1)) {
            if (!(VAR(intrfr2_t2) == 2)) {
                if (!(VAR(intrfr2_t1) == 1)) {
                    FPx = t44;
                    FPy = t39;
                } else if (!(VAR(intrfr2_t1) == 1)) {
                    FPx = t44;
                    FPy = t36;
                } else if (!(VAR(intrfr2_t1) == 1)) {
                    if (!(VAR(intrfr2_t1) == 2)) {
                        FPx = t44;
                        FPy = t38;
                    } else {
                        FPx = t44;
                        FPy = t37;
                    }
                }
            } else if (!(VAR(intrfr2_t2) == 2)) {
                if (VAR(intrfr2_t1) == 1) {
                    FPx = t44;
                    FPy = t19;
                } else if (VAR(intrfr2_t1) == 1) {
                    FPx = t44;
                    FPy = t12;
                } else if (VAR(intrfr2_t1) == 1) {
                    if (VAR(intrfr2_t2) == 2) {
                        FPx = t44;
                        FPy = t17;
                    } else {
                        FPx = t44;
                        FPy = t15;
                    }
                }
            } else if (!(VAR(intrfr2_t2) == 2)) {
                if (VAR(intrfr2_t1) == 2) {
                    if (!(VAR(intrfr2_t1) == 1)) {
                        FPx = t44;
                        FPy = t34;
                    } else if (!(VAR(intrfr2_t1) == 1)) {
                        FPx = t44;
                        FPy = t29;
                    } else if (!(VAR(intrfr2_t1) == 1)) {
                        if (0.0 > t20) {
                            FPx = t44;
                            FPy = t33;
                        } else {
                            FPx = t44;
                            FPy = t31;
                        }
                    }
                } else {
                    if (!(VAR(intrfr2_t1) == 1)) {
                        FPx = t44;
                        FPy = t27;
                    } else if (!(VAR(intrfr2_t1) == 1)) {
                        FPx = t44;
                        FPy = t22;
                    } else if (!(VAR(intrfr2_t1) == 1)) {
                        if (!(0.0 > t20)) {
                            FPx = t44;
                            FPy = t26;
                        } else {
                            FPx = t44;
                            FPy = t24;
                        }
                    }
                }
            }
        } else if (VAR(intrfr2_t2) == 1) {
            if (!(VAR(intrfr2_t1) == 1)) {
                if (!(VAR(intrfr2_t1) == 2)) {
                    FPx = t7;
                    FPy = t39;
                } else if (!(VAR(intrfr2_t1) == 2)) {
                    FPx = t7;
                    FPy = t36;
                } else if (!(VAR(intrfr2_t1) == 2)) {
                    if (VAR(intrfr2_t2) == 2) {
                        FPx = t7;
                        FPy = t38;
                    } else {
                        FPx = t7;
                        FPy = t37;
                    }
                }
            } else if (VAR(intrfr2_t1) == 1) {
                if (!(VAR(intrfr2_t2) == 1)) {
                    FPx = t7;
                    FPy = t19;
                } else if (VAR(intrfr2_t2) == 1) {
                    FPx = t7;
                    FPy = t12;
                } else if (VAR(intrfr2_t2) == 2) {
                    if (!(VAR(intrfr2_t2) == 1)) {
                        FPx = t7;
                        FPy = t17;
                    } else {
                        FPx = t7;
                        FPy = t15;
                    }
                }
            } else if (VAR(intrfr2_t1) == 2) {
                if (!(VAR(intrfr2_t1) == 1)) {
                    if (0.0 > t20) {
                        FPx = t7;
                        FPy = t34;
                    } else if (0.0 > t20) {
                        FPx = t7;
                        FPy = t29;
                    } else if (0.0 > t20) {
                        if (VAR(intrfr2_t2) == 2) {
                            FPx = t7;
                            FPy = t33;
                        } else {
                            FPx = t7;
                            FPy = t31;
                        }
                    }
                } else {
                    if (!(0.0 > t20)) {
                        FPx = t7;
                        FPy = t27;
                    } else if (!(0.0 > t20)) {
                        FPx = t7;
                        FPy = t22;
                    } else if (!(0.0 > t20)) {
                        if (VAR(intrfr2_t2) == 2) {
                            FPx = t7;
                            FPy = t26;
                        } else {
                            FPx = t7;
                            FPy = t24;
                        }
                    }
                }
            }
        } else if (VAR(intrfr2_t2) == 2) {
            if (!(VAR(intrfr2_t2) == 1)) {
                if (0.0 > t40) {
                    if (!(VAR(intrfr2_t1) == 1)) {
                        FPx = t42;
                        FPy = t39;
                    } else if (!(VAR(intrfr2_t1) == 1)) {
                        FPx = t42;
                        FPy = t36;
                    } else if (!(VAR(intrfr2_t1) == 1)) {
                        if (!(VAR(intrfr2_t1) == 2)) {
                            FPx = t42;
                            FPy = t38;
                        } else {
                            FPx = t42;
                            FPy = t37;
                        }
                    }
                } else if (0.0 > t40) {
                    if (VAR(intrfr2_t1) == 1) {
                        FPx = t42;
                        FPy = t19;
                    } else if (VAR(intrfr2_t1) == 1) {
                        FPx = t42;
                        FPy = t12;
                    } else if (VAR(intrfr2_t1) == 1) {
                        if (VAR(intrfr2_t2) == 2) {
                            FPx = t42;
                            FPy = t17;
                        } else {
                            FPx = t42;
                            FPy = t15;
                        }
                    }
                } else if (0.0 > t40) {
                    if (VAR(intrfr2_t1) == 2) {
                        if (!(VAR(intrfr2_t1) == 1)) {
                            FPx = t42;
                            FPy = t34;
                        } else if (!(VAR(intrfr2_t1) == 1)) {
                            FPx = t42;
                            FPy = t29;
                        } else if (!(VAR(intrfr2_t1) == 1)) {
                            if (0.0 > t20) {
                                FPx = t42;
                                FPy = t33;
                            } else {
                                FPx = t42;
                                FPy = t31;
                            }
                        }
                    } else {
                        if (!(VAR(intrfr2_t1) == 1)) {
                            FPx = t42;
                            FPy = t27;
                        } else if (!(VAR(intrfr2_t1) == 1)) {
                            FPx = t42;
                            FPy = t22;
                        } else if (!(VAR(intrfr2_t1) == 1)) {
                            if (!(0.0 > t20)) {
                                FPx = t42;
                                FPy = t26;
                            } else {
                                FPx = t42;
                                FPy = t24;
                            }
                        }
                    }
                }
            } else {
                if (!(0.0 > t40)) {
                    if (!(VAR(intrfr2_t1) == 1)) {
                        FPx = t41;
                        FPy = t39;
                    } else if (!(VAR(intrfr2_t1) == 1)) {
                        FPx = t41;
                        FPy = t36;
                    } else if (!(VAR(intrfr2_t1) == 1)) {
                        if (!(VAR(intrfr2_t1) == 2)) {
                            FPx = t41;
                            FPy = t38;
                        } else {
                            FPx = t41;
                            FPy = t37;
                        }
                    }
                } else if (!(0.0 > t40)) {
                    if (VAR(intrfr2_t1) == 1) {
                        FPx = t41;
                        FPy = t19;
                    } else if (VAR(intrfr2_t1) == 1) {
                        FPx = t41;
                        FPy = t12;
                    } else if (VAR(intrfr2_t1) == 1) {
                        if (VAR(intrfr2_t2) == 2) {
                            FPx = t41;
                            FPy = t17;
                        } else {
                            FPx = t41;
                            FPy = t15;
                        }
                    }
                } else if (!(0.0 > t40)) {
                    if (VAR(intrfr2_t1) == 2) {
                        if (!(VAR(intrfr2_t1) == 1)) {
                            FPx = t41;
                            FPy = t34;
                        } else if (!(VAR(intrfr2_t1) == 1)) {
                            FPx = t41;
                            FPy = t29;
                        } else if (!(VAR(intrfr2_t1) == 1)) {
                            if (0.0 > t20) {
                                FPx = t41;
                                FPy = t33;
                            } else {
                                FPx = t41;
                                FPy = t31;
                            }
                        }
                    } else {
                        if (!(VAR(intrfr2_t1) == 1)) {
                            FPx = t41;
                            FPy = t27;
                        } else if (!(VAR(intrfr2_t1) == 1)) {
                            FPx = t41;
                            FPy = t22;
                        } else if (!(VAR(intrfr2_t1) == 1)) {
                            if (!(0.0 > t20)) {
                                FPx = t41;
                                FPy = t26;
                            } else {
                                FPx = t41;
                                FPy = t24;
                            }
                        }
                    }
                }
            }
        }
    } else if (VAR(intrfr2_t1) == 2) {
        if (!(VAR(intrfr2_t1) == 1)) {
            if (0.0 > t45) {
                if (!(VAR(intrfr2_t2) == 1)) {
                    if (!(VAR(intrfr2_t2) == 2)) {
                        FPx = t53;
                        FPy = t39;
                    } else if (!(VAR(intrfr2_t2) == 2)) {
                        FPx = t53;
                        FPy = t36;
                    } else if (!(VAR(intrfr2_t2) == 2)) {
                        if (!(VAR(intrfr2_t1) == 1)) {
                            FPx = t53;
                            FPy = t38;
                        } else {
                            FPx = t53;
                            FPy = t37;
                        }
                    }
                } else if (!(VAR(intrfr2_t2) == 1)) {
                    if (!(VAR(intrfr2_t2) == 2)) {
                        FPx = t53;
                        FPy = t19;
                    } else if (!(VAR(intrfr2_t2) == 2)) {
                        FPx = t53;
                        FPy = t12;
                    } else if (!(VAR(intrfr2_t2) == 2)) {
                        if (VAR(intrfr2_t1) == 1) {
                            FPx = t53;
                            FPy = t17;
                        } else {
                            FPx = t53;
                            FPy = t15;
                        }
                    }
                } else if (!(VAR(intrfr2_t2) == 1)) {
                    if (!(VAR(intrfr2_t2) == 2)) {
                        if (VAR(intrfr2_t1) == 2) {
                            FPx = t53;
                            FPy = t34;
                        } else if (VAR(intrfr2_t1) == 2) {
                            FPx = t53;
                            FPy = t29;
                        } else if (VAR(intrfr2_t1) == 2) {
                            if (!(VAR(intrfr2_t1) == 1)) {
                                FPx = t53;
                                FPy = t33;
                            } else {
                                FPx = t53;
                                FPy = t31;
                            }
                        }
                    } else {
                        if (VAR(intrfr2_t1) == 2) {
                            FPx = t53;
                            FPy = t27;
                        } else if (VAR(intrfr2_t1) == 2) {
                            FPx = t53;
                            FPy = t22;
                        } else if (VAR(intrfr2_t1) == 2) {
                            if (!(VAR(intrfr2_t1) == 1)) {
                                FPx = t53;
                                FPy = t26;
                            } else {
                                FPx = t53;
                                FPy = t24;
                            }
                        }
                    }
                }
            } else if (0.0 > t45) {
                if (VAR(intrfr2_t2) == 1) {
                    if (!(VAR(intrfr2_t1) == 1)) {
                        FPx = t50;
                        FPy = t39;
                    } else if (!(VAR(intrfr2_t1) == 1)) {
                        FPx = t50;
                        FPy = t36;
                    } else if (!(VAR(intrfr2_t1) == 1)) {
                        if (!(VAR(intrfr2_t1) == 2)) {
                            FPx = t50;
                            FPy = t38;
                        } else {
                            FPx = t50;
                            FPy = t37;
                        }
                    }
                } else if (VAR(intrfr2_t2) == 1) {
                    if (VAR(intrfr2_t1) == 1) {
                        FPx = t50;
                        FPy = t19;
                    } else if (VAR(intrfr2_t1) == 1) {
                        FPx = t50;
                        FPy = t12;
                    } else if (VAR(intrfr2_t1) == 1) {
                        if (VAR(intrfr2_t2) == 2) {
                            FPx = t50;
                            FPy = t17;
                        } else {
                            FPx = t50;
                            FPy = t15;
                        }
                    }
                } else if (VAR(intrfr2_t2) == 1) {
                    if (VAR(intrfr2_t1) == 2) {
                        if (!(VAR(intrfr2_t1) == 1)) {
                            FPx = t50;
                            FPy = t34;
                        } else if (!(VAR(intrfr2_t1) == 1)) {
                            FPx = t50;
                            FPy = t29;
                        } else if (!(VAR(intrfr2_t1) == 1)) {
                            if (0.0 > t20) {
                                FPx = t50;
                                FPy = t33;
                            } else {
                                FPx = t50;
                                FPy = t31;
                            }
                        }
                    } else {
                        if (!(VAR(intrfr2_t1) == 1)) {
                            FPx = t50;
                            FPy = t27;
                        } else if (!(VAR(intrfr2_t1) == 1)) {
                            FPx = t50;
                            FPy = t22;
                        } else if (!(VAR(intrfr2_t1) == 1)) {
                            if (!(0.0 > t20)) {
                                FPx = t50;
                                FPy = t26;
                            } else {
                                FPx = t50;
                                FPy = t24;
                            }
                        }
                    }
                }
            } else if (0.0 > t45) {
                if (VAR(intrfr2_t2) == 2) {
                    if (!(VAR(intrfr2_t2) == 1)) {
                        if (0.0 > t40) {
                            FPx = t52;
                            FPy = t39;
                        } else if (0.0 > t40) {
                            FPx = t52;
                            FPy = t36;
                        } else if (0.0 > t40) {
                            if (!(VAR(intrfr2_t1) == 1)) {
                                FPx = t52;
                                FPy = t38;
                            } else {
                                FPx = t52;
                                FPy = t37;
                            }
                        }
                    } else if (!(VAR(intrfr2_t2) == 1)) {
                        if (0.0 > t40) {
                            FPx = t52;
                            FPy = t19;
                        } else if (0.0 > t40) {
                            FPx = t52;
                            FPy = t12;
                        } else if (0.0 > t40) {
                            if (VAR(intrfr2_t1) == 1) {
                                FPx = t52;
                                FPy = t17;
                            } else {
                                FPx = t52;
                                FPy = t15;
                            }
                        }
                    } else if (!(VAR(intrfr2_t2) == 1)) {
                        if (0.0 > t40) {
                            if (VAR(intrfr2_t1) == 2) {
                                FPx = t52;
                                FPy = t34;
                            } else if (VAR(intrfr2_t1) == 2) {
                                FPx = t52;
                                FPy = t29;
                            } else if (VAR(intrfr2_t1) == 2) {
                                if (!(VAR(intrfr2_t1) == 1)) {
                                    FPx = t52;
                                    FPy = t33;
                                } else {
                                    FPx = t52;
                                    FPy = t31;
                                }
                            }
                        } else {
                            if (VAR(intrfr2_t1) == 2) {
                                FPx = t52;
                                FPy = t27;
                            } else if (VAR(intrfr2_t1) == 2) {
                                FPx = t52;
                                FPy = t22;
                            } else if (VAR(intrfr2_t1) == 2) {
                                if (!(VAR(intrfr2_t1) == 1)) {
                                    FPx = t52;
                                    FPy = t26;
                                } else {
                                    FPx = t52;
                                    FPy = t24;
                                }
                            }
                        }
                    }
                } else {
                    if (!(VAR(intrfr2_t2) == 1)) {
                        if (!(0.0 > t40)) {
                            FPx = t51;
                            FPy = t39;
                        } else if (!(0.0 > t40)) {
                            FPx = t51;
                            FPy = t36;
                        } else if (!(0.0 > t40)) {
                            if (!(VAR(intrfr2_t1) == 1)) {
                                FPx = t51;
                                FPy = t38;
                            } else {
                                FPx = t51;
                                FPy = t37;
                            }
                        }
                    } else if (!(VAR(intrfr2_t2) == 1)) {
                        if (!(0.0 > t40)) {
                            FPx = t51;
                            FPy = t19;
                        } else if (!(0.0 > t40)) {
                            FPx = t51;
                            FPy = t12;
                        } else if (!(0.0 > t40)) {
                            if (VAR(intrfr2_t1) == 1) {
                                FPx = t51;
                                FPy = t17;
                            } else {
                                FPx = t51;
                                FPy = t15;
                            }
                        }
                    } else if (!(VAR(intrfr2_t2) == 1)) {
                        if (!(0.0 > t40)) {
                            if (VAR(intrfr2_t1) == 2) {
                                FPx = t51;
                                FPy = t34;
                            } else if (VAR(intrfr2_t1) == 2) {
                                FPx = t51;
                                FPy = t29;
                            } else if (VAR(intrfr2_t1) == 2) {
                                if (!(VAR(intrfr2_t1) == 1)) {
                                    FPx = t51;
                                    FPy = t33;
                                } else {
                                    FPx = t51;
                                    FPy = t31;
                                }
                            }
                        } else {
                            if (VAR(intrfr2_t1) == 2) {
                                FPx = t51;
                                FPy = t27;
                            } else if (VAR(intrfr2_t1) == 2) {
                                FPx = t51;
                                FPy = t22;
                            } else if (VAR(intrfr2_t1) == 2) {
                                if (!(VAR(intrfr2_t1) == 1)) {
                                    FPx = t51;
                                    FPy = t26;
                                } else {
                                    FPx = t51;
                                    FPy = t24;
                                }
                            }
                        }
                    }
                }
            }
        } else {
            if (!(0.0 > t45)) {
                if (!(VAR(intrfr2_t2) == 1)) {
                    if (!(VAR(intrfr2_t2) == 2)) {
                        FPx = t49;
                        FPy = t39;
                    } else if (!(VAR(intrfr2_t2) == 2)) {
                        FPx = t49;
                        FPy = t36;
                    } else if (!(VAR(intrfr2_t2) == 2)) {
                        if (!(VAR(intrfr2_t1) == 1)) {
                            FPx = t49;
                            FPy = t38;
                        } else {
                            FPx = t49;
                            FPy = t37;
                        }
                    }
                } else if (!(VAR(intrfr2_t2) == 1)) {
                    if (!(VAR(intrfr2_t2) == 2)) {
                        FPx = t49;
                        FPy = t19;
                    } else if (!(VAR(intrfr2_t2) == 2)) {
                        FPx = t49;
                        FPy = t12;
                    } else if (!(VAR(intrfr2_t2) == 2)) {
                        if (VAR(intrfr2_t1) == 1) {
                            FPx = t49;
                            FPy = t17;
                        } else {
                            FPx = t49;
                            FPy = t15;
                        }
                    }
                } else if (!(VAR(intrfr2_t2) == 1)) {
                    if (!(VAR(intrfr2_t2) == 2)) {
                        if (VAR(intrfr2_t1) == 2) {
                            FPx = t49;
                            FPy = t34;
                        } else if (VAR(intrfr2_t1) == 2) {
                            FPx = t49;
                            FPy = t29;
                        } else if (VAR(intrfr2_t1) == 2) {
                            if (!(VAR(intrfr2_t1) == 1)) {
                                FPx = t49;
                                FPy = t33;
                            } else {
                                FPx = t49;
                                FPy = t31;
                            }
                        }
                    } else {
                        if (VAR(intrfr2_t1) == 2) {
                            FPx = t49;
                            FPy = t27;
                        } else if (VAR(intrfr2_t1) == 2) {
                            FPx = t49;
                            FPy = t22;
                        } else if (VAR(intrfr2_t1) == 2) {
                            if (!(VAR(intrfr2_t1) == 1)) {
                                FPx = t49;
                                FPy = t26;
                            } else {
                                FPx = t49;
                                FPy = t24;
                            }
                        }
                    }
                }
            } else if (!(0.0 > t45)) {
                if (VAR(intrfr2_t2) == 1) {
                    if (!(VAR(intrfr2_t1) == 1)) {
                        FPx = t46;
                        FPy = t39;
                    } else if (!(VAR(intrfr2_t1) == 1)) {
                        FPx = t46;
                        FPy = t36;
                    } else if (!(VAR(intrfr2_t1) == 1)) {
                        if (!(VAR(intrfr2_t1) == 2)) {
                            FPx = t46;
                            FPy = t38;
                        } else {
                            FPx = t46;
                            FPy = t37;
                        }
                    }
                } else if (VAR(intrfr2_t2) == 1) {
                    if (VAR(intrfr2_t1) == 1) {
                        FPx = t46;
                        FPy = t19;
                    } else if (VAR(intrfr2_t1) == 1) {
                        FPx = t46;
                        FPy = t12;
                    } else if (VAR(intrfr2_t1) == 1) {
                        if (VAR(intrfr2_t2) == 2) {
                            FPx = t46;
                            FPy = t17;
                        } else {
                            FPx = t46;
                            FPy = t15;
                        }
                    }
                } else if (VAR(intrfr2_t2) == 1) {
                    if (VAR(intrfr2_t1) == 2) {
                        if (!(VAR(intrfr2_t1) == 1)) {
                            FPx = t46;
                            FPy = t34;
                        } else if (!(VAR(intrfr2_t1) == 1)) {
                            FPx = t46;
                            FPy = t29;
                        } else if (!(VAR(intrfr2_t1) == 1)) {
                            if (0.0 > t20) {
                                FPx = t46;
                                FPy = t33;
                            } else {
                                FPx = t46;
                                FPy = t31;
                            }
                        }
                    } else {
                        if (!(VAR(intrfr2_t1) == 1)) {
                            FPx = t46;
                            FPy = t27;
                        } else if (!(VAR(intrfr2_t1) == 1)) {
                            FPx = t46;
                            FPy = t22;
                        } else if (!(VAR(intrfr2_t1) == 1)) {
                            if (!(0.0 > t20)) {
                                FPx = t46;
                                FPy = t26;
                            } else {
                                FPx = t46;
                                FPy = t24;
                            }
                        }
                    }
                }
            } else if (!(0.0 > t45)) {
                if (VAR(intrfr2_t2) == 2) {
                    if (!(VAR(intrfr2_t2) == 1)) {
                        if (0.0 > t40) {
                            FPx = t48;
                            FPy = t39;
                        } else if (0.0 > t40) {
                            FPx = t48;
                            FPy = t36;
                        } else if (0.0 > t40) {
                            if (!(VAR(intrfr2_t1) == 1)) {
                                FPx = t48;
                                FPy = t38;
                            } else {
                                FPx = t48;
                                FPy = t37;
                            }
                        }
                    } else if (!(VAR(intrfr2_t2) == 1)) {
                        if (0.0 > t40) {
                            FPx = t48;
                            FPy = t19;
                        } else if (0.0 > t40) {
                            FPx = t48;
                            FPy = t12;
                        } else if (0.0 > t40) {
                            if (VAR(intrfr2_t1) == 1) {
                                FPx = t48;
                                FPy = t17;
                            } else {
                                FPx = t48;
                                FPy = t15;
                            }
                        }
                    } else if (!(VAR(intrfr2_t2) == 1)) {
                        if (0.0 > t40) {
                            if (VAR(intrfr2_t1) == 2) {
                                FPx = t48;
                                FPy = t34;
                            } else if (VAR(intrfr2_t1) == 2) {
                                FPx = t48;
                                FPy = t29;
                            } else if (VAR(intrfr2_t1) == 2) {
                                if (!(VAR(intrfr2_t1) == 1)) {
                                    FPx = t48;
                                    FPy = t33;
                                } else {
                                    FPx = t48;
                                    FPy = t31;
                                }
                            }
                        } else {
                            if (VAR(intrfr2_t1) == 2) {
                                FPx = t48;
                                FPy = t27;
                            } else if (VAR(intrfr2_t1) == 2) {
                                FPx = t48;
                                FPy = t22;
                            } else if (VAR(intrfr2_t1) == 2) {
                                if (!(VAR(intrfr2_t1) == 1)) {
                                    FPx = t48;
                                    FPy = t26;
                                } else {
                                    FPx = t48;
                                    FPy = t24;
                                }
                            }
                        }
                    }
                } else {
                    if (!(VAR(intrfr2_t2) == 1)) {
                        if (!(0.0 > t40)) {
                            FPx = t47;
                            FPy = t39;
                        } else if (!(0.0 > t40)) {
                            FPx = t47;
                            FPy = t36;
                        } else if (!(0.0 > t40)) {
                            if (!(VAR(intrfr2_t1) == 1)) {
                                FPx = t47;
                                FPy = t38;
                            } else {
                                FPx = t47;
                                FPy = t37;
                            }
                        }
                    } else if (!(VAR(intrfr2_t2) == 1)) {
                        if (!(0.0 > t40)) {
                            FPx = t47;
                            FPy = t19;
                        } else if (!(0.0 > t40)) {
                            FPx = t47;
                            FPy = t12;
                        } else if (!(0.0 > t40)) {
                            if (VAR(intrfr2_t1) == 1) {
                                FPx = t47;
                                FPy = t17;
                            } else {
                                FPx = t47;
                                FPy = t15;
                            }
                        }
                    } else if (!(VAR(intrfr2_t2) == 1)) {
                        if (!(0.0 > t40)) {
                            if (VAR(intrfr2_t1) == 2) {
                                FPx = t47;
                                FPy = t34;
                            } else if (VAR(intrfr2_t1) == 2) {
                                FPx = t47;
                                FPy = t29;
                            } else if (VAR(intrfr2_t1) == 2) {
                                if (!(VAR(intrfr2_t1) == 1)) {
                                    FPx = t47;
                                    FPy = t33;
                                } else {
                                    FPx = t47;
                                    FPy = t31;
                                }
                            }
                        } else {
                            if (VAR(intrfr2_t1) == 2) {
                                FPx = t47;
                                FPy = t27;
                            } else if (VAR(intrfr2_t1) == 2) {
                                FPx = t47;
                                FPy = t22;
                            } else if (VAR(intrfr2_t1) == 2) {
                                if (!(VAR(intrfr2_t1) == 1)) {
                                    FPx = t47;
                                    FPy = t26;
                                } else {
                                    FPx = t47;
                                    FPy = t24;
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    return TRUE;
}