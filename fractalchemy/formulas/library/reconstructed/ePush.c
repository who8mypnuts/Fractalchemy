/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        ePush.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from ePush.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double ePush_push;
    double ePush_dist;
    double ePush_rotate;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("ePush");
APO_VARIABLES(
    VAR_REAL(ePush_push, 0.0),
    VAR_REAL(ePush_dist, 1.0),
    VAR_REAL_CYCLE(ePush_rotate, -M_PI, M_PI, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTx * FTx + FTy * FTy + 1.0;
    double t2 = FTx + FTx;
    double t3 = t1 + t2;
    double t4 = t1 - t2;
    double t5 = sqrt(t3);
    double t6 = sqrt(t4);
    double t7 = 0.5 * (t5 + t6);
    double t8 = acos(FTx);
    double t9 = -t8 + VAR(ePush_rotate);
    double t10 = exp(acosh(1.0) * VAR(ePush_dist) + VAR(ePush_push));
    double t11 = 1.0 / t10;
    double t12 = 0.5 * (t11 + t10) * VVAR;
    double t13 = cos(t9) * t12 + FPx;
    double t14 = 0.5 * (t10 - t11) * VVAR;
    double t15 = sin(t9) * t14 + FPy;
    double t16 = t8 + VAR(ePush_rotate);
    double t17 = cos(t16) * t12 + FPx;
    double t18 = sin(t16) * t14 + FPy;
    double t19 = acos(-1.0);
    double t20 = -t19 + VAR(ePush_rotate);
    double t21 = cos(t20);
    double t22 = t21 * t12 + FPx;
    double t23 = sin(t20);
    double t24 = t23 * t14 + FPy;
    double t25 = t19 + VAR(ePush_rotate);
    double t26 = cos(t25);
    double t27 = t26 * t12 + FPx;
    double t28 = sin(t25);
    double t29 = t28 * t14 + FPy;
    double t30 = acos(1.0);
    double t31 = -t30 + VAR(ePush_rotate);
    double t32 = cos(t31);
    double t33 = t32 * t12 + FPx;
    double t34 = sin(t31);
    double t35 = t34 * t14 + FPy;
    double t36 = t30 + VAR(ePush_rotate);
    double t37 = cos(t36);
    double t38 = t37 * t12 + FPx;
    double t39 = sin(t36);
    double t40 = t39 * t14 + FPy;
    double t41 = (1.0 / t7) * FTx;
    double t42 = acos(t41);
    double t43 = -t42 + VAR(ePush_rotate);
    double t44 = exp(acosh(t7) * VAR(ePush_dist) + VAR(ePush_push));
    double t45 = 1.0 / t44;
    double t46 = 0.5 * (t45 + t44) * VVAR;
    double t47 = 0.5 * (t44 - t45) * VVAR;
    double t48 = t42 + VAR(ePush_rotate);
    double t49 = 0.5 * t5;
    double t50 = (1.0 / t49) * FTx;
    double t51 = acos(t50);
    double t52 = -t51 + VAR(ePush_rotate);
    double t53 = exp(acosh(t49) * VAR(ePush_dist) + VAR(ePush_push));
    double t54 = 1.0 / t53;
    double t55 = 0.5 * (t54 + t53) * VVAR;
    double t56 = 0.5 * (t53 - t54) * VVAR;
    double t57 = t51 + VAR(ePush_rotate);
    double t58 = 0.5 * t6;
    double t59 = (1.0 / t58) * FTx;
    double t60 = acos(t59);
    double t61 = -t60 + VAR(ePush_rotate);
    double t62 = exp(acosh(t58) * VAR(ePush_dist) + VAR(ePush_push));
    double t63 = 1.0 / t62;
    double t64 = 0.5 * (t63 + t62) * VVAR;
    double t65 = 0.5 * (t62 - t63) * VVAR;
    double t66 = t60 + VAR(ePush_rotate);
    double t67 = (1.0 / 0.0) * FTx;
    double t68 = acos(t67);
    double t69 = -t68 + VAR(ePush_rotate);
    double t70 = exp(acosh(0.0) * VAR(ePush_dist) + VAR(ePush_push));
    double t71 = 1.0 / t70;
    double t72 = 0.5 * (t71 + t70) * VVAR;
    double t73 = 0.5 * (t70 - t71) * VVAR;
    double t74 = t68 + VAR(ePush_rotate);
    if (t3 <= 0.0) {
        if (0.0 >= t4) {
            if (0.0 >= 1.0) {
                if (t67 > 1.0) {
                    if (FTy >= 0.0) {
                        FPx = t37 * t72 + FPx;
                        FPy = t39 * t73 + FPy;
                    } else {
                        FPx = t32 * t72 + FPx;
                        FPy = t34 * t73 + FPy;
                    }
                } else {
                    if (-1.0 > t67) {
                        if (FTy >= 0.0) {
                            FPx = t26 * t72 + FPx;
                            FPy = t28 * t73 + FPy;
                        } else {
                            FPx = t21 * t72 + FPx;
                            FPy = t23 * t73 + FPy;
                        }
                    } else {
                        if (FTy >= 0.0) {
                            FPx = cos(t74) * t72 + FPx;
                            FPy = sin(t74) * t73 + FPy;
                        } else {
                            FPx = cos(t69) * t72 + FPx;
                            FPy = sin(t69) * t73 + FPy;
                        }
                    }
                }
            } else {
                if (FTx > 1.0) {
                    if (FTy >= 0.0) {
                        FPx = t38;
                        FPy = t40;
                    } else {
                        FPx = t33;
                        FPy = t35;
                    }
                } else {
                    if (-1.0 > FTx) {
                        if (FTy >= 0.0) {
                            FPx = t27;
                            FPy = t29;
                        } else {
                            FPx = t22;
                            FPy = t24;
                        }
                    } else {
                        if (FTy >= 0.0) {
                            FPx = t17;
                            FPy = t18;
                        } else {
                            FPx = t13;
                            FPy = t15;
                        }
                    }
                }
            }
        } else {
            if (t58 >= 1.0) {
                if (t59 > 1.0) {
                    if (FTy >= 0.0) {
                        FPx = t37 * t64 + FPx;
                        FPy = t39 * t65 + FPy;
                    } else {
                        FPx = t32 * t64 + FPx;
                        FPy = t34 * t65 + FPy;
                    }
                } else {
                    if (-1.0 > t59) {
                        if (FTy >= 0.0) {
                            FPx = t26 * t64 + FPx;
                            FPy = t28 * t65 + FPy;
                        } else {
                            FPx = t21 * t64 + FPx;
                            FPy = t23 * t65 + FPy;
                        }
                    } else {
                        if (FTy >= 0.0) {
                            FPx = cos(t66) * t64 + FPx;
                            FPy = sin(t66) * t65 + FPy;
                        } else {
                            FPx = cos(t61) * t64 + FPx;
                            FPy = sin(t61) * t65 + FPy;
                        }
                    }
                }
            } else {
                if (FTx > 1.0) {
                    if (FTy >= 0.0) {
                        FPx = t38;
                        FPy = t40;
                    } else {
                        FPx = t33;
                        FPy = t35;
                    }
                } else {
                    if (-1.0 > FTx) {
                        if (FTy >= 0.0) {
                            FPx = t27;
                            FPy = t29;
                        } else {
                            FPx = t22;
                            FPy = t24;
                        }
                    } else {
                        if (FTy >= 0.0) {
                            FPx = t17;
                            FPy = t18;
                        } else {
                            FPx = t13;
                            FPy = t15;
                        }
                    }
                }
            }
        }
    } else {
        if (0.0 >= t4) {
            if (t49 >= 1.0) {
                if (t50 > 1.0) {
                    if (FTy >= 0.0) {
                        FPx = t37 * t55 + FPx;
                        FPy = t39 * t56 + FPy;
                    } else {
                        FPx = t32 * t55 + FPx;
                        FPy = t34 * t56 + FPy;
                    }
                } else {
                    if (-1.0 > t50) {
                        if (FTy >= 0.0) {
                            FPx = t26 * t55 + FPx;
                            FPy = t28 * t56 + FPy;
                        } else {
                            FPx = t21 * t55 + FPx;
                            FPy = t23 * t56 + FPy;
                        }
                    } else {
                        if (FTy >= 0.0) {
                            FPx = cos(t57) * t55 + FPx;
                            FPy = sin(t57) * t56 + FPy;
                        } else {
                            FPx = cos(t52) * t55 + FPx;
                            FPy = sin(t52) * t56 + FPy;
                        }
                    }
                }
            } else {
                if (FTx > 1.0) {
                    if (FTy >= 0.0) {
                        FPx = t38;
                        FPy = t40;
                    } else {
                        FPx = t33;
                        FPy = t35;
                    }
                } else {
                    if (-1.0 > FTx) {
                        if (FTy >= 0.0) {
                            FPx = t27;
                            FPy = t29;
                        } else {
                            FPx = t22;
                            FPy = t24;
                        }
                    } else {
                        if (FTy >= 0.0) {
                            FPx = t17;
                            FPy = t18;
                        } else {
                            FPx = t13;
                            FPy = t15;
                        }
                    }
                }
            }
        } else {
            if (t7 >= 1.0) {
                if (t41 > 1.0) {
                    if (FTy >= 0.0) {
                        FPx = t37 * t46 + FPx;
                        FPy = t39 * t47 + FPy;
                    } else {
                        FPx = t32 * t46 + FPx;
                        FPy = t34 * t47 + FPy;
                    }
                } else {
                    if (-1.0 > t41) {
                        if (FTy >= 0.0) {
                            FPx = t26 * t46 + FPx;
                            FPy = t28 * t47 + FPy;
                        } else {
                            FPx = t21 * t46 + FPx;
                            FPy = t23 * t47 + FPy;
                        }
                    } else {
                        if (FTy >= 0.0) {
                            FPx = cos(t48) * t46 + FPx;
                            FPy = sin(t48) * t47 + FPy;
                        } else {
                            FPx = cos(t43) * t46 + FPx;
                            FPy = sin(t43) * t47 + FPy;
                        }
                    }
                }
            } else {
                if (FTx > 1.0) {
                    if (FTy >= 0.0) {
                        FPx = t38;
                        FPy = t40;
                    } else {
                        FPx = t33;
                        FPy = t35;
                    }
                } else {
                    if (-1.0 > FTx) {
                        if (FTy >= 0.0) {
                            FPx = t27;
                            FPy = t29;
                        } else {
                            FPx = t22;
                            FPy = t24;
                        }
                    } else {
                        if (FTy >= 0.0) {
                            FPx = t17;
                            FPy = t18;
                        } else {
                            FPx = t13;
                            FPy = t15;
                        }
                    }
                }
            }
        }
    }
    return TRUE;
}