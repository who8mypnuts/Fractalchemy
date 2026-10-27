/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        eCollide.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from eCollide.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double eCollide_a;
    int eCollide_num;
    double m_10;
    double m_18;
    double m_20;
    double m_28;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("eCollide");
APO_VARIABLES(
    VAR_REAL_CYCLE(eCollide_a, 0.0, 1.0, 0.0),
    VAR_INTEGER_NONZERO(eCollide_num, 1)
);

int PluginVarPrepare(Variation* vp)
{
    double t1 = 1.0 / (double)VAR(eCollide_num);
    double t2 = M_PI * VAR(eCollide_a);
    VAR(m_18) = M_1_PI * (double)VAR(eCollide_num);
    VAR(m_28) = M_PI * t1;
    VAR(m_10) = t2;
    VAR(m_20) = t1 * t2;
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
    double t9 = (double)(int)(VAR(m_18) * t8) * VAR(m_28);
    double t10 = fmod(t8 + VAR(m_20), VAR(m_28)) + t9;
    double t11 = cos(t10) * VVAR + FPx;
    double t12 = sqrt(2.0) * (sqrt(0.0) * VVAR);
    double t13 = sin(t10) * t12 + FPy;
    double t14 = fmod(t8 - VAR(m_20), VAR(m_28)) + t9;
    double t15 = cos(t14) * VVAR + FPx;
    double t16 = sin(t14) * t12 + FPy;
    double t17 = -t10;
    double t18 = cos(t17) * VVAR + FPx;
    double t19 = sin(t17) * t12 + FPy;
    double t20 = -t14;
    double t21 = cos(t20) * VVAR + FPx;
    double t22 = sin(t20) * t12 + FPy;
    double t23 = acos(-1.0);
    double t24 = (double)(int)(VAR(m_18) * t23) * VAR(m_28);
    double t25 = fmod(t23 + VAR(m_20), VAR(m_28)) + t24;
    double t26 = cos(t25);
    double t27 = t26 * VVAR + FPx;
    double t28 = sin(t25);
    double t29 = t28 * t12 + FPy;
    double t30 = fmod(t23 - VAR(m_20), VAR(m_28)) + t24;
    double t31 = cos(t30);
    double t32 = t31 * VVAR + FPx;
    double t33 = sin(t30);
    double t34 = t33 * t12 + FPy;
    double t35 = -t25;
    double t36 = cos(t35);
    double t37 = t36 * VVAR + FPx;
    double t38 = sin(t35);
    double t39 = t38 * t12 + FPy;
    double t40 = -t30;
    double t41 = cos(t40);
    double t42 = t41 * VVAR + FPx;
    double t43 = sin(t40);
    double t44 = t43 * t12 + FPy;
    double t45 = acos(1.0);
    double t46 = (double)(int)(VAR(m_18) * t45) * VAR(m_28);
    double t47 = fmod(t45 + VAR(m_20), VAR(m_28)) + t46;
    double t48 = cos(t47);
    double t49 = t48 * VVAR + FPx;
    double t50 = sin(t47);
    double t51 = t50 * t12 + FPy;
    double t52 = fmod(t45 - VAR(m_20), VAR(m_28)) + t46;
    double t53 = cos(t52);
    double t54 = t53 * VVAR + FPx;
    double t55 = sin(t52);
    double t56 = t55 * t12 + FPy;
    double t57 = -t47;
    double t58 = cos(t57);
    double t59 = t58 * VVAR + FPx;
    double t60 = sin(t57);
    double t61 = t60 * t12 + FPy;
    double t62 = -t52;
    double t63 = cos(t62);
    double t64 = t63 * VVAR + FPx;
    double t65 = sin(t62);
    double t66 = t65 * t12 + FPy;
    double t67 = (1.0 / t7) * FTx;
    double t68 = acos(t67);
    double t69 = (double)(int)(VAR(m_18) * t68) * VAR(m_28);
    double t70 = fmod(t68 + VAR(m_20), VAR(m_28)) + t69;
    double t71 = t7 * VVAR;
    double t72 = sqrt(t7 + 1.0) * (sqrt(t7 - 1.0) * VVAR);
    double t73 = fmod(t68 - VAR(m_20), VAR(m_28)) + t69;
    double t74 = -t70;
    double t75 = -t73;
    double t76 = 0.5 * t5;
    double t77 = (1.0 / t76) * FTx;
    double t78 = acos(t77);
    double t79 = (double)(int)(VAR(m_18) * t78) * VAR(m_28);
    double t80 = fmod(t78 + VAR(m_20), VAR(m_28)) + t79;
    double t81 = t76 * VVAR;
    double t82 = sqrt(t76 + 1.0) * (sqrt(t76 - 1.0) * VVAR);
    double t83 = fmod(t78 - VAR(m_20), VAR(m_28)) + t79;
    double t84 = -t80;
    double t85 = -t83;
    double t86 = 0.5 * t6;
    double t87 = (1.0 / t86) * FTx;
    double t88 = acos(t87);
    double t89 = (double)(int)(VAR(m_18) * t88) * VAR(m_28);
    double t90 = fmod(t88 + VAR(m_20), VAR(m_28)) + t89;
    double t91 = t86 * VVAR;
    double t92 = sqrt(t86 + 1.0) * (sqrt(t86 - 1.0) * VVAR);
    double t93 = fmod(t88 - VAR(m_20), VAR(m_28)) + t89;
    double t94 = -t90;
    double t95 = -t93;
    double t96 = (1.0 / 0.0) * FTx;
    double t97 = acos(t96);
    double t98 = (double)(int)(VAR(m_18) * t97) * VAR(m_28);
    double t99 = fmod(t97 + VAR(m_20), VAR(m_28)) + t98;
    double t100 = 0.0 * VVAR;
    double t101 = sqrt(1.0) * (sqrt(-1.0) * VVAR);
    double t102 = fmod(t97 - VAR(m_20), VAR(m_28)) + t98;
    double t103 = -t99;
    double t104 = -t102;
    if (t3 <= 0.0) {
        if (t4 <= 0.0) {
            if (0.0 >= 1.0) {
                if (t96 > 1.0) {
                    if (FTy <= 0.0) {
                        if (((int)(VAR(m_18) * t45) & 1) != 0) {
                            FPx = t63 * t100 + FPx;
                            FPy = t65 * t101 + FPy;
                        } else {
                            FPx = t58 * t100 + FPx;
                            FPy = t60 * t101 + FPy;
                        }
                    } else {
                        if (((int)(VAR(m_18) * t45) & 1) != 0) {
                            FPx = t53 * t100 + FPx;
                            FPy = t55 * t101 + FPy;
                        } else {
                            FPx = t48 * t100 + FPx;
                            FPy = t50 * t101 + FPy;
                        }
                    }
                } else {
                    if (-1.0 > t96) {
                        if (FTy <= 0.0) {
                            if (((int)(VAR(m_18) * t23) & 1) != 0) {
                                FPx = t41 * t100 + FPx;
                                FPy = t43 * t101 + FPy;
                            } else {
                                FPx = t36 * t100 + FPx;
                                FPy = t38 * t101 + FPy;
                            }
                        } else {
                            if (((int)(VAR(m_18) * t23) & 1) != 0) {
                                FPx = t31 * t100 + FPx;
                                FPy = t33 * t101 + FPy;
                            } else {
                                FPx = t26 * t100 + FPx;
                                FPy = t28 * t101 + FPy;
                            }
                        }
                    } else {
                        if (FTy <= 0.0) {
                            if (((int)(VAR(m_18) * t97) & 1) != 0) {
                                FPx = cos(t104) * t100 + FPx;
                                FPy = sin(t104) * t101 + FPy;
                            } else {
                                FPx = cos(t103) * t100 + FPx;
                                FPy = sin(t103) * t101 + FPy;
                            }
                        } else {
                            if (((int)(VAR(m_18) * t97) & 1) != 0) {
                                FPx = cos(t102) * t100 + FPx;
                                FPy = sin(t102) * t101 + FPy;
                            } else {
                                FPx = cos(t99) * t100 + FPx;
                                FPy = sin(t99) * t101 + FPy;
                            }
                        }
                    }
                }
            } else {
                if (FTx > 1.0) {
                    if (FTy <= 0.0) {
                        if (((int)(VAR(m_18) * t45) & 1) != 0) {
                            FPx = t64;
                            FPy = t66;
                        } else {
                            FPx = t59;
                            FPy = t61;
                        }
                    } else {
                        if (((int)(VAR(m_18) * t45) & 1) != 0) {
                            FPx = t54;
                            FPy = t56;
                        } else {
                            FPx = t49;
                            FPy = t51;
                        }
                    }
                } else {
                    if (-1.0 > FTx) {
                        if (FTy <= 0.0) {
                            if (((int)(VAR(m_18) * t23) & 1) != 0) {
                                FPx = t42;
                                FPy = t44;
                            } else {
                                FPx = t37;
                                FPy = t39;
                            }
                        } else {
                            if (((int)(VAR(m_18) * t23) & 1) != 0) {
                                FPx = t32;
                                FPy = t34;
                            } else {
                                FPx = t27;
                                FPy = t29;
                            }
                        }
                    } else {
                        if (FTy <= 0.0) {
                            if (((int)(VAR(m_18) * t8) & 1) != 0) {
                                FPx = t21;
                                FPy = t22;
                            } else {
                                FPx = t18;
                                FPy = t19;
                            }
                        } else {
                            if (((int)(VAR(m_18) * t8) & 1) != 0) {
                                FPx = t15;
                                FPy = t16;
                            } else {
                                FPx = t11;
                                FPy = t13;
                            }
                        }
                    }
                }
            }
        } else {
            if (t86 >= 1.0) {
                if (t87 > 1.0) {
                    if (FTy <= 0.0) {
                        if (((int)(VAR(m_18) * t45) & 1) != 0) {
                            FPx = t63 * t91 + FPx;
                            FPy = t65 * t92 + FPy;
                        } else {
                            FPx = t58 * t91 + FPx;
                            FPy = t60 * t92 + FPy;
                        }
                    } else {
                        if (((int)(VAR(m_18) * t45) & 1) != 0) {
                            FPx = t53 * t91 + FPx;
                            FPy = t55 * t92 + FPy;
                        } else {
                            FPx = t48 * t91 + FPx;
                            FPy = t50 * t92 + FPy;
                        }
                    }
                } else {
                    if (-1.0 > t87) {
                        if (FTy <= 0.0) {
                            if (((int)(VAR(m_18) * t23) & 1) != 0) {
                                FPx = t41 * t91 + FPx;
                                FPy = t43 * t92 + FPy;
                            } else {
                                FPx = t36 * t91 + FPx;
                                FPy = t38 * t92 + FPy;
                            }
                        } else {
                            if (((int)(VAR(m_18) * t23) & 1) != 0) {
                                FPx = t31 * t91 + FPx;
                                FPy = t33 * t92 + FPy;
                            } else {
                                FPx = t26 * t91 + FPx;
                                FPy = t28 * t92 + FPy;
                            }
                        }
                    } else {
                        if (FTy <= 0.0) {
                            if (((int)(VAR(m_18) * t88) & 1) != 0) {
                                FPx = cos(t95) * t91 + FPx;
                                FPy = sin(t95) * t92 + FPy;
                            } else {
                                FPx = cos(t94) * t91 + FPx;
                                FPy = sin(t94) * t92 + FPy;
                            }
                        } else {
                            if (((int)(VAR(m_18) * t88) & 1) != 0) {
                                FPx = cos(t93) * t91 + FPx;
                                FPy = sin(t93) * t92 + FPy;
                            } else {
                                FPx = cos(t90) * t91 + FPx;
                                FPy = sin(t90) * t92 + FPy;
                            }
                        }
                    }
                }
            } else {
                if (FTx > 1.0) {
                    if (FTy <= 0.0) {
                        if (((int)(VAR(m_18) * t45) & 1) != 0) {
                            FPx = t64;
                            FPy = t66;
                        } else {
                            FPx = t59;
                            FPy = t61;
                        }
                    } else {
                        if (((int)(VAR(m_18) * t45) & 1) != 0) {
                            FPx = t54;
                            FPy = t56;
                        } else {
                            FPx = t49;
                            FPy = t51;
                        }
                    }
                } else {
                    if (-1.0 > FTx) {
                        if (FTy <= 0.0) {
                            if (((int)(VAR(m_18) * t23) & 1) != 0) {
                                FPx = t42;
                                FPy = t44;
                            } else {
                                FPx = t37;
                                FPy = t39;
                            }
                        } else {
                            if (((int)(VAR(m_18) * t23) & 1) != 0) {
                                FPx = t32;
                                FPy = t34;
                            } else {
                                FPx = t27;
                                FPy = t29;
                            }
                        }
                    } else {
                        if (FTy <= 0.0) {
                            if (((int)(VAR(m_18) * t8) & 1) != 0) {
                                FPx = t21;
                                FPy = t22;
                            } else {
                                FPx = t18;
                                FPy = t19;
                            }
                        } else {
                            if (((int)(VAR(m_18) * t8) & 1) != 0) {
                                FPx = t15;
                                FPy = t16;
                            } else {
                                FPx = t11;
                                FPy = t13;
                            }
                        }
                    }
                }
            }
        }
    } else {
        if (t4 <= 0.0) {
            if (t76 >= 1.0) {
                if (t77 > 1.0) {
                    if (FTy <= 0.0) {
                        if (((int)(VAR(m_18) * t45) & 1) != 0) {
                            FPx = t63 * t81 + FPx;
                            FPy = t65 * t82 + FPy;
                        } else {
                            FPx = t58 * t81 + FPx;
                            FPy = t60 * t82 + FPy;
                        }
                    } else {
                        if (((int)(VAR(m_18) * t45) & 1) != 0) {
                            FPx = t53 * t81 + FPx;
                            FPy = t55 * t82 + FPy;
                        } else {
                            FPx = t48 * t81 + FPx;
                            FPy = t50 * t82 + FPy;
                        }
                    }
                } else {
                    if (-1.0 > t77) {
                        if (FTy <= 0.0) {
                            if (((int)(VAR(m_18) * t23) & 1) != 0) {
                                FPx = t41 * t81 + FPx;
                                FPy = t43 * t82 + FPy;
                            } else {
                                FPx = t36 * t81 + FPx;
                                FPy = t38 * t82 + FPy;
                            }
                        } else {
                            if (((int)(VAR(m_18) * t23) & 1) != 0) {
                                FPx = t31 * t81 + FPx;
                                FPy = t33 * t82 + FPy;
                            } else {
                                FPx = t26 * t81 + FPx;
                                FPy = t28 * t82 + FPy;
                            }
                        }
                    } else {
                        if (FTy <= 0.0) {
                            if (((int)(VAR(m_18) * t78) & 1) != 0) {
                                FPx = cos(t85) * t81 + FPx;
                                FPy = sin(t85) * t82 + FPy;
                            } else {
                                FPx = cos(t84) * t81 + FPx;
                                FPy = sin(t84) * t82 + FPy;
                            }
                        } else {
                            if (((int)(VAR(m_18) * t78) & 1) != 0) {
                                FPx = cos(t83) * t81 + FPx;
                                FPy = sin(t83) * t82 + FPy;
                            } else {
                                FPx = cos(t80) * t81 + FPx;
                                FPy = sin(t80) * t82 + FPy;
                            }
                        }
                    }
                }
            } else {
                if (FTx > 1.0) {
                    if (FTy <= 0.0) {
                        if (((int)(VAR(m_18) * t45) & 1) != 0) {
                            FPx = t64;
                            FPy = t66;
                        } else {
                            FPx = t59;
                            FPy = t61;
                        }
                    } else {
                        if (((int)(VAR(m_18) * t45) & 1) != 0) {
                            FPx = t54;
                            FPy = t56;
                        } else {
                            FPx = t49;
                            FPy = t51;
                        }
                    }
                } else {
                    if (-1.0 > FTx) {
                        if (FTy <= 0.0) {
                            if (((int)(VAR(m_18) * t23) & 1) != 0) {
                                FPx = t42;
                                FPy = t44;
                            } else {
                                FPx = t37;
                                FPy = t39;
                            }
                        } else {
                            if (((int)(VAR(m_18) * t23) & 1) != 0) {
                                FPx = t32;
                                FPy = t34;
                            } else {
                                FPx = t27;
                                FPy = t29;
                            }
                        }
                    } else {
                        if (FTy <= 0.0) {
                            if (((int)(VAR(m_18) * t8) & 1) != 0) {
                                FPx = t21;
                                FPy = t22;
                            } else {
                                FPx = t18;
                                FPy = t19;
                            }
                        } else {
                            if (((int)(VAR(m_18) * t8) & 1) != 0) {
                                FPx = t15;
                                FPy = t16;
                            } else {
                                FPx = t11;
                                FPy = t13;
                            }
                        }
                    }
                }
            }
        } else {
            if (t7 >= 1.0) {
                if (t67 > 1.0) {
                    if (FTy <= 0.0) {
                        if (((int)(VAR(m_18) * t45) & 1) != 0) {
                            FPx = t63 * t71 + FPx;
                            FPy = t65 * t72 + FPy;
                        } else {
                            FPx = t58 * t71 + FPx;
                            FPy = t60 * t72 + FPy;
                        }
                    } else {
                        if (((int)(VAR(m_18) * t45) & 1) != 0) {
                            FPx = t53 * t71 + FPx;
                            FPy = t55 * t72 + FPy;
                        } else {
                            FPx = t48 * t71 + FPx;
                            FPy = t50 * t72 + FPy;
                        }
                    }
                } else {
                    if (-1.0 > t67) {
                        if (FTy <= 0.0) {
                            if (((int)(VAR(m_18) * t23) & 1) != 0) {
                                FPx = t41 * t71 + FPx;
                                FPy = t43 * t72 + FPy;
                            } else {
                                FPx = t36 * t71 + FPx;
                                FPy = t38 * t72 + FPy;
                            }
                        } else {
                            if (((int)(VAR(m_18) * t23) & 1) != 0) {
                                FPx = t31 * t71 + FPx;
                                FPy = t33 * t72 + FPy;
                            } else {
                                FPx = t26 * t71 + FPx;
                                FPy = t28 * t72 + FPy;
                            }
                        }
                    } else {
                        if (FTy <= 0.0) {
                            if (((int)(VAR(m_18) * t68) & 1) != 0) {
                                FPx = cos(t75) * t71 + FPx;
                                FPy = sin(t75) * t72 + FPy;
                            } else {
                                FPx = cos(t74) * t71 + FPx;
                                FPy = sin(t74) * t72 + FPy;
                            }
                        } else {
                            if (((int)(VAR(m_18) * t68) & 1) != 0) {
                                FPx = cos(t73) * t71 + FPx;
                                FPy = sin(t73) * t72 + FPy;
                            } else {
                                FPx = cos(t70) * t71 + FPx;
                                FPy = sin(t70) * t72 + FPy;
                            }
                        }
                    }
                }
            } else {
                if (FTx > 1.0) {
                    if (FTy <= 0.0) {
                        if (((int)(VAR(m_18) * t45) & 1) != 0) {
                            FPx = t64;
                            FPy = t66;
                        } else {
                            FPx = t59;
                            FPy = t61;
                        }
                    } else {
                        if (((int)(VAR(m_18) * t45) & 1) != 0) {
                            FPx = t54;
                            FPy = t56;
                        } else {
                            FPx = t49;
                            FPy = t51;
                        }
                    }
                } else {
                    if (-1.0 > FTx) {
                        if (FTy <= 0.0) {
                            if (((int)(VAR(m_18) * t23) & 1) != 0) {
                                FPx = t42;
                                FPy = t44;
                            } else {
                                FPx = t37;
                                FPy = t39;
                            }
                        } else {
                            if (((int)(VAR(m_18) * t23) & 1) != 0) {
                                FPx = t32;
                                FPy = t34;
                            } else {
                                FPx = t27;
                                FPy = t29;
                            }
                        }
                    } else {
                        if (FTy <= 0.0) {
                            if (((int)(VAR(m_18) * t8) & 1) != 0) {
                                FPx = t21;
                                FPy = t22;
                            } else {
                                FPx = t18;
                                FPy = t19;
                            }
                        } else {
                            if (((int)(VAR(m_18) * t8) & 1) != 0) {
                                FPx = t15;
                                FPy = t16;
                            } else {
                                FPx = t11;
                                FPy = t13;
                            }
                        }
                    }
                }
            }
        }
    }
    return TRUE;
}