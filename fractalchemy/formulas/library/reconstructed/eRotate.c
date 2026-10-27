/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        eRotate.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from eRotate.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double eRotate_rotate;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("eRotate");
APO_VARIABLES(
    VAR_REAL_CYCLE(eRotate_rotate, -M_PI, M_PI, 0.0)
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
    double t8 = acos(1.0);
    double t9 = fmod(-t8 + VAR(eRotate_rotate) + M_PI, M_2PI) - M_PI;
    double t10 = cos(t9);
    double t11 = t10 * VVAR + FPx;
    double t12 = sin(t9);
    double t13 = sqrt(2.0) * (sqrt(0.0) * VVAR);
    double t14 = t12 * t13 + FPy;
    double t15 = fmod(t8 + VAR(eRotate_rotate) + M_PI, M_2PI) - M_PI;
    double t16 = cos(t15);
    double t17 = t16 * VVAR + FPx;
    double t18 = sin(t15);
    double t19 = t18 * t13 + FPy;
    double t20 = acos(-1.0);
    double t21 = fmod(-t20 + VAR(eRotate_rotate) + M_PI, M_2PI) - M_PI;
    double t22 = cos(t21);
    double t23 = t22 * VVAR + FPx;
    double t24 = sin(t21);
    double t25 = t24 * t13 + FPy;
    double t26 = fmod(t20 + VAR(eRotate_rotate) + M_PI, M_2PI) - M_PI;
    double t27 = cos(t26);
    double t28 = t27 * VVAR + FPx;
    double t29 = sin(t26);
    double t30 = t29 * t13 + FPy;
    double t31 = acos(FTx);
    double t32 = fmod(-t31 + VAR(eRotate_rotate) + M_PI, M_2PI) - M_PI;
    double t33 = cos(t32) * VVAR + FPx;
    double t34 = sin(t32) * t13 + FPy;
    double t35 = fmod(t31 + VAR(eRotate_rotate) + M_PI, M_2PI) - M_PI;
    double t36 = cos(t35) * VVAR + FPx;
    double t37 = sin(t35) * t13 + FPy;
    double t38 = (1.0 / t7) * FTx;
    double t39 = VVAR * t7;
    double t40 = sqrt(t7 + 1.0) * (sqrt(t7 - 1.0) * VVAR);
    double t41 = acos(t38);
    double t42 = fmod(-t41 + VAR(eRotate_rotate) + M_PI, M_2PI) - M_PI;
    double t43 = fmod(t41 + VAR(eRotate_rotate) + M_PI, M_2PI) - M_PI;
    double t44 = 0.5 * t5;
    double t45 = (1.0 / t44) * FTx;
    double t46 = VVAR * t44;
    double t47 = sqrt(t44 + 1.0) * (sqrt(t44 - 1.0) * VVAR);
    double t48 = acos(t45);
    double t49 = fmod(-t48 + VAR(eRotate_rotate) + M_PI, M_2PI) - M_PI;
    double t50 = fmod(t48 + VAR(eRotate_rotate) + M_PI, M_2PI) - M_PI;
    double t51 = 0.5 * t6;
    double t52 = (1.0 / t51) * FTx;
    double t53 = VVAR * t51;
    double t54 = sqrt(t51 + 1.0) * (sqrt(t51 - 1.0) * VVAR);
    double t55 = acos(t52);
    double t56 = fmod(-t55 + VAR(eRotate_rotate) + M_PI, M_2PI) - M_PI;
    double t57 = fmod(t55 + VAR(eRotate_rotate) + M_PI, M_2PI) - M_PI;
    double t58 = (1.0 / 0.0) * FTx;
    double t59 = 0.0 * VVAR;
    double t60 = sqrt(1.0) * (sqrt(-1.0) * VVAR);
    double t61 = acos(t58);
    double t62 = fmod(-t61 + VAR(eRotate_rotate) + M_PI, M_2PI) - M_PI;
    double t63 = fmod(t61 + VAR(eRotate_rotate) + M_PI, M_2PI) - M_PI;
    if (t3 <= 0.0) {
        if (t4 <= 0.0) {
            if (0.0 >= 1.0) {
                if (t58 <= 1.0) {
                    if (-1.0 <= t58) {
                        if (FTy >= 0.0) {
                            FPx = cos(t63) * t59 + FPx;
                            FPy = sin(t63) * t60 + FPy;
                        } else {
                            FPx = cos(t62) * t59 + FPx;
                            FPy = sin(t62) * t60 + FPy;
                        }
                    } else {
                        if (FTy >= 0.0) {
                            FPx = t27 * t59 + FPx;
                            FPy = t29 * t60 + FPy;
                        } else {
                            FPx = t22 * t59 + FPx;
                            FPy = t24 * t60 + FPy;
                        }
                    }
                } else {
                    if (FTy >= 0.0) {
                        FPx = t16 * t59 + FPx;
                        FPy = t18 * t60 + FPy;
                    } else {
                        FPx = t10 * t59 + FPx;
                        FPy = t12 * t60 + FPy;
                    }
                }
            } else {
                if (FTx <= 1.0) {
                    if (-1.0 <= FTx) {
                        if (FTy >= 0.0) {
                            FPx = t36;
                            FPy = t37;
                        } else {
                            FPx = t33;
                            FPy = t34;
                        }
                    } else {
                        if (FTy >= 0.0) {
                            FPx = t28;
                            FPy = t30;
                        } else {
                            FPx = t23;
                            FPy = t25;
                        }
                    }
                } else {
                    if (FTy >= 0.0) {
                        FPx = t17;
                        FPy = t19;
                    } else {
                        FPx = t11;
                        FPy = t14;
                    }
                }
            }
        } else {
            if (t51 >= 1.0) {
                if (t52 <= 1.0) {
                    if (-1.0 <= t52) {
                        if (FTy >= 0.0) {
                            FPx = cos(t57) * t53 + FPx;
                            FPy = sin(t57) * t54 + FPy;
                        } else {
                            FPx = cos(t56) * t53 + FPx;
                            FPy = sin(t56) * t54 + FPy;
                        }
                    } else {
                        if (FTy >= 0.0) {
                            FPx = t27 * t53 + FPx;
                            FPy = t29 * t54 + FPy;
                        } else {
                            FPx = t22 * t53 + FPx;
                            FPy = t24 * t54 + FPy;
                        }
                    }
                } else {
                    if (FTy >= 0.0) {
                        FPx = t16 * t53 + FPx;
                        FPy = t18 * t54 + FPy;
                    } else {
                        FPx = t10 * t53 + FPx;
                        FPy = t12 * t54 + FPy;
                    }
                }
            } else {
                if (FTx <= 1.0) {
                    if (-1.0 <= FTx) {
                        if (FTy >= 0.0) {
                            FPx = t36;
                            FPy = t37;
                        } else {
                            FPx = t33;
                            FPy = t34;
                        }
                    } else {
                        if (FTy >= 0.0) {
                            FPx = t28;
                            FPy = t30;
                        } else {
                            FPx = t23;
                            FPy = t25;
                        }
                    }
                } else {
                    if (FTy >= 0.0) {
                        FPx = t17;
                        FPy = t19;
                    } else {
                        FPx = t11;
                        FPy = t14;
                    }
                }
            }
        }
    } else {
        if (t4 <= 0.0) {
            if (t44 >= 1.0) {
                if (t45 <= 1.0) {
                    if (-1.0 <= t45) {
                        if (FTy >= 0.0) {
                            FPx = cos(t50) * t46 + FPx;
                            FPy = sin(t50) * t47 + FPy;
                        } else {
                            FPx = cos(t49) * t46 + FPx;
                            FPy = sin(t49) * t47 + FPy;
                        }
                    } else {
                        if (FTy >= 0.0) {
                            FPx = t27 * t46 + FPx;
                            FPy = t29 * t47 + FPy;
                        } else {
                            FPx = t22 * t46 + FPx;
                            FPy = t24 * t47 + FPy;
                        }
                    }
                } else {
                    if (FTy >= 0.0) {
                        FPx = t16 * t46 + FPx;
                        FPy = t18 * t47 + FPy;
                    } else {
                        FPx = t10 * t46 + FPx;
                        FPy = t12 * t47 + FPy;
                    }
                }
            } else {
                if (FTx <= 1.0) {
                    if (-1.0 <= FTx) {
                        if (FTy >= 0.0) {
                            FPx = t36;
                            FPy = t37;
                        } else {
                            FPx = t33;
                            FPy = t34;
                        }
                    } else {
                        if (FTy >= 0.0) {
                            FPx = t28;
                            FPy = t30;
                        } else {
                            FPx = t23;
                            FPy = t25;
                        }
                    }
                } else {
                    if (FTy >= 0.0) {
                        FPx = t17;
                        FPy = t19;
                    } else {
                        FPx = t11;
                        FPy = t14;
                    }
                }
            }
        } else {
            if (t7 >= 1.0) {
                if (t38 <= 1.0) {
                    if (-1.0 <= t38) {
                        if (FTy >= 0.0) {
                            FPx = cos(t43) * t39 + FPx;
                            FPy = sin(t43) * t40 + FPy;
                        } else {
                            FPx = cos(t42) * t39 + FPx;
                            FPy = sin(t42) * t40 + FPy;
                        }
                    } else {
                        if (FTy >= 0.0) {
                            FPx = t27 * t39 + FPx;
                            FPy = t29 * t40 + FPy;
                        } else {
                            FPx = t22 * t39 + FPx;
                            FPy = t24 * t40 + FPy;
                        }
                    }
                } else {
                    if (FTy >= 0.0) {
                        FPx = t16 * t39 + FPx;
                        FPy = t18 * t40 + FPy;
                    } else {
                        FPx = t10 * t39 + FPx;
                        FPy = t12 * t40 + FPy;
                    }
                }
            } else {
                if (FTx <= 1.0) {
                    if (-1.0 <= FTx) {
                        if (FTy >= 0.0) {
                            FPx = t36;
                            FPy = t37;
                        } else {
                            FPx = t33;
                            FPy = t34;
                        }
                    } else {
                        if (FTy >= 0.0) {
                            FPx = t28;
                            FPy = t30;
                        } else {
                            FPx = t23;
                            FPy = t25;
                        }
                    }
                } else {
                    if (FTy >= 0.0) {
                        FPx = t17;
                        FPy = t19;
                    } else {
                        FPx = t11;
                        FPy = t14;
                    }
                }
            }
        }
    }
    return TRUE;
}