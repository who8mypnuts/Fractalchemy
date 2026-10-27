/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        eJulia.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from eJulia.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    int eJulia_power;
    double m_10;
    double m_8;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("eJulia");
APO_VARIABLES(
    VAR_INTEGER(eJulia_power, 0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_10) = VAR(eJulia_power) >> 31 | 1;
    VAR(m_8) = fabs((double)VAR(eJulia_power));
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTx * FTx + FTy * FTy;
    double t2 = 1.0 / t1;
    double t3 = t2 + 1.0;
    double t4 = FTx * t2;
    double t5 = t4 + t4;
    double t6 = t3 + t5;
    double t7 = t3 - t5;
    double t8 = sqrt(t6);
    double t9 = sqrt(t7);
    double t10 = 0.5 * (t8 + t9);
    double t11 = 1.0 / (double)VAR(eJulia_power);
    double t12 = floor(random01() * (double)VAR(eJulia_power)) * (M_2PI * t11);
    double t13 = acos(t4);
    double t14 = t12 + -t13 * t11;
    double t15 = exp(t11 * acosh(1.0));
    double t16 = 1.0 / t15;
    double t17 = 0.5 * (t15 + t16) * VVAR;
    double t18 = cos(t14) * t17 + FPx;
    double t19 = 0.5 * (t15 - t16) * VVAR;
    double t20 = sin(t14) * t19 + FPy;
    double t21 = t12 + t13 * t11;
    double t22 = cos(t21) * t17 + FPx;
    double t23 = sin(t21) * t19 + FPy;
    double t24 = acos(-1.0);
    double t25 = t12 + -t24 * t11;
    double t26 = cos(t25);
    double t27 = t26 * t17 + FPx;
    double t28 = sin(t25);
    double t29 = t28 * t19 + FPy;
    double t30 = t12 + t24 * t11;
    double t31 = cos(t30);
    double t32 = t31 * t17 + FPx;
    double t33 = sin(t30);
    double t34 = t33 * t19 + FPy;
    double t35 = acos(1.0);
    double t36 = t12 + -t35 * t11;
    double t37 = cos(t36);
    double t38 = t37 * t17 + FPx;
    double t39 = sin(t36);
    double t40 = t39 * t19 + FPy;
    double t41 = t12 + t35 * t11;
    double t42 = cos(t41);
    double t43 = t42 * t17 + FPx;
    double t44 = sin(t41);
    double t45 = t44 * t19 + FPy;
    double t46 = (1.0 / t10) * t4;
    double t47 = acos(t46);
    double t48 = t12 + -t47 * t11;
    double t49 = exp(t11 * acosh(t10));
    double t50 = 1.0 / t49;
    double t51 = 0.5 * (t49 + t50) * VVAR;
    double t52 = 0.5 * (t49 - t50) * VVAR;
    double t53 = t12 + t47 * t11;
    double t54 = 0.5 * t8;
    double t55 = (1.0 / t54) * t4;
    double t56 = acos(t55);
    double t57 = t12 + -t56 * t11;
    double t58 = exp(t11 * acosh(t54));
    double t59 = 1.0 / t58;
    double t60 = 0.5 * (t58 + t59) * VVAR;
    double t61 = 0.5 * (t58 - t59) * VVAR;
    double t62 = t12 + t56 * t11;
    double t63 = 0.5 * t9;
    double t64 = (1.0 / t63) * t4;
    double t65 = acos(t64);
    double t66 = t12 + -t65 * t11;
    double t67 = exp(t11 * acosh(t63));
    double t68 = 1.0 / t67;
    double t69 = 0.5 * (t67 + t68) * VVAR;
    double t70 = 0.5 * (t67 - t68) * VVAR;
    double t71 = t12 + t65 * t11;
    double t72 = 1.0 / 0.0;
    double t73 = t72 * t4;
    double t74 = acos(t73);
    double t75 = t12 + -t74 * t11;
    double t76 = exp(t11 * acosh(0.0));
    double t77 = 1.0 / t76;
    double t78 = 0.5 * (t76 + t77) * VVAR;
    double t79 = 0.5 * (t76 - t77) * VVAR;
    double t80 = t12 + t74 * t11;
    double t81 = t26 * t78 + FPx;
    double t82 = t28 * t79 + FPy;
    double t83 = t31 * t78 + FPx;
    double t84 = t33 * t79 + FPy;
    double t85 = t37 * t78 + FPx;
    double t86 = t39 * t79 + FPy;
    double t87 = t42 * t78 + FPx;
    double t88 = t44 * t79 + FPy;
    double t89 = t1 + 1.0;
    double t90 = FTx + FTx;
    double t91 = t89 + t90;
    double t92 = t89 - t90;
    double t93 = sqrt(t91);
    double t94 = sqrt(t92);
    double t95 = 0.5 * (t93 + t94);
    double t96 = acos(FTx);
    double t97 = t12 + -t96 * t11;
    double t98 = cos(t97) * t17 + FPx;
    double t99 = sin(t97) * t19 + FPy;
    double t100 = t12 + t96 * t11;
    double t101 = cos(t100) * t17 + FPx;
    double t102 = sin(t100) * t19 + FPy;
    double t103 = (1.0 / t95) * FTx;
    double t104 = acos(t103);
    double t105 = t12 + -t104 * t11;
    double t106 = exp(t11 * acosh(t95));
    double t107 = 1.0 / t106;
    double t108 = 0.5 * (t106 + t107) * VVAR;
    double t109 = 0.5 * (t106 - t107) * VVAR;
    double t110 = t12 + t104 * t11;
    double t111 = 0.5 * t93;
    double t112 = (1.0 / t111) * FTx;
    double t113 = acos(t112);
    double t114 = t12 + -t113 * t11;
    double t115 = exp(t11 * acosh(t111));
    double t116 = 1.0 / t115;
    double t117 = 0.5 * (t115 + t116) * VVAR;
    double t118 = 0.5 * (t115 - t116) * VVAR;
    double t119 = t12 + t113 * t11;
    double t120 = 0.5 * t94;
    double t121 = (1.0 / t120) * FTx;
    double t122 = acos(t121);
    double t123 = t12 + -t122 * t11;
    double t124 = exp(t11 * acosh(t120));
    double t125 = 1.0 / t124;
    double t126 = 0.5 * (t124 + t125) * VVAR;
    double t127 = 0.5 * (t124 - t125) * VVAR;
    double t128 = t12 + t122 * t11;
    double t129 = t72 * FTx;
    double t130 = acos(t129);
    double t131 = t12 + -t130 * t11;
    double t132 = t12 + t130 * t11;
    if (VAR(m_10) == 1) {
        if (t91 <= 0.0) {
            if (0.0 >= t92) {
                if (0.0 >= 1.0) {
                    if (t129 > 1.0) {
                        if (FTy >= 0.0) {
                            FPx = t87;
                            FPy = t88;
                        } else {
                            FPx = t85;
                            FPy = t86;
                        }
                    } else {
                        if (-1.0 > t129) {
                            if (FTy >= 0.0) {
                                FPx = t83;
                                FPy = t84;
                            } else {
                                FPx = t81;
                                FPy = t82;
                            }
                        } else {
                            if (FTy >= 0.0) {
                                FPx = cos(t132) * t78 + FPx;
                                FPy = sin(t132) * t79 + FPy;
                            } else {
                                FPx = cos(t131) * t78 + FPx;
                                FPy = sin(t131) * t79 + FPy;
                            }
                        }
                    }
                } else {
                    if (FTx > 1.0) {
                        if (FTy >= 0.0) {
                            FPx = t43;
                            FPy = t45;
                        } else {
                            FPx = t38;
                            FPy = t40;
                        }
                    } else {
                        if (-1.0 > FTx) {
                            if (FTy >= 0.0) {
                                FPx = t32;
                                FPy = t34;
                            } else {
                                FPx = t27;
                                FPy = t29;
                            }
                        } else {
                            if (FTy >= 0.0) {
                                FPx = t101;
                                FPy = t102;
                            } else {
                                FPx = t98;
                                FPy = t99;
                            }
                        }
                    }
                }
            } else {
                if (t120 >= 1.0) {
                    if (t121 > 1.0) {
                        if (FTy >= 0.0) {
                            FPx = t42 * t126 + FPx;
                            FPy = t44 * t127 + FPy;
                        } else {
                            FPx = t37 * t126 + FPx;
                            FPy = t39 * t127 + FPy;
                        }
                    } else {
                        if (-1.0 > t121) {
                            if (FTy >= 0.0) {
                                FPx = t31 * t126 + FPx;
                                FPy = t33 * t127 + FPy;
                            } else {
                                FPx = t26 * t126 + FPx;
                                FPy = t28 * t127 + FPy;
                            }
                        } else {
                            if (FTy >= 0.0) {
                                FPx = cos(t128) * t126 + FPx;
                                FPy = sin(t128) * t127 + FPy;
                            } else {
                                FPx = cos(t123) * t126 + FPx;
                                FPy = sin(t123) * t127 + FPy;
                            }
                        }
                    }
                } else {
                    if (FTx > 1.0) {
                        if (FTy >= 0.0) {
                            FPx = t43;
                            FPy = t45;
                        } else {
                            FPx = t38;
                            FPy = t40;
                        }
                    } else {
                        if (-1.0 > FTx) {
                            if (FTy >= 0.0) {
                                FPx = t32;
                                FPy = t34;
                            } else {
                                FPx = t27;
                                FPy = t29;
                            }
                        } else {
                            if (FTy >= 0.0) {
                                FPx = t101;
                                FPy = t102;
                            } else {
                                FPx = t98;
                                FPy = t99;
                            }
                        }
                    }
                }
            }
        } else {
            if (0.0 >= t92) {
                if (t111 >= 1.0) {
                    if (t112 > 1.0) {
                        if (FTy >= 0.0) {
                            FPx = t42 * t117 + FPx;
                            FPy = t44 * t118 + FPy;
                        } else {
                            FPx = t37 * t117 + FPx;
                            FPy = t39 * t118 + FPy;
                        }
                    } else {
                        if (-1.0 > t112) {
                            if (FTy >= 0.0) {
                                FPx = t31 * t117 + FPx;
                                FPy = t33 * t118 + FPy;
                            } else {
                                FPx = t26 * t117 + FPx;
                                FPy = t28 * t118 + FPy;
                            }
                        } else {
                            if (FTy >= 0.0) {
                                FPx = cos(t119) * t117 + FPx;
                                FPy = sin(t119) * t118 + FPy;
                            } else {
                                FPx = cos(t114) * t117 + FPx;
                                FPy = sin(t114) * t118 + FPy;
                            }
                        }
                    }
                } else {
                    if (FTx > 1.0) {
                        if (FTy >= 0.0) {
                            FPx = t43;
                            FPy = t45;
                        } else {
                            FPx = t38;
                            FPy = t40;
                        }
                    } else {
                        if (-1.0 > FTx) {
                            if (FTy >= 0.0) {
                                FPx = t32;
                                FPy = t34;
                            } else {
                                FPx = t27;
                                FPy = t29;
                            }
                        } else {
                            if (FTy >= 0.0) {
                                FPx = t101;
                                FPy = t102;
                            } else {
                                FPx = t98;
                                FPy = t99;
                            }
                        }
                    }
                }
            } else {
                if (t95 >= 1.0) {
                    if (t103 > 1.0) {
                        if (FTy >= 0.0) {
                            FPx = t42 * t108 + FPx;
                            FPy = t44 * t109 + FPy;
                        } else {
                            FPx = t37 * t108 + FPx;
                            FPy = t39 * t109 + FPy;
                        }
                    } else {
                        if (-1.0 > t103) {
                            if (FTy >= 0.0) {
                                FPx = t31 * t108 + FPx;
                                FPy = t33 * t109 + FPy;
                            } else {
                                FPx = t26 * t108 + FPx;
                                FPy = t28 * t109 + FPy;
                            }
                        } else {
                            if (FTy >= 0.0) {
                                FPx = cos(t110) * t108 + FPx;
                                FPy = sin(t110) * t109 + FPy;
                            } else {
                                FPx = cos(t105) * t108 + FPx;
                                FPy = sin(t105) * t109 + FPy;
                            }
                        }
                    }
                } else {
                    if (FTx > 1.0) {
                        if (FTy >= 0.0) {
                            FPx = t43;
                            FPy = t45;
                        } else {
                            FPx = t38;
                            FPy = t40;
                        }
                    } else {
                        if (-1.0 > FTx) {
                            if (FTy >= 0.0) {
                                FPx = t32;
                                FPy = t34;
                            } else {
                                FPx = t27;
                                FPy = t29;
                            }
                        } else {
                            if (FTy >= 0.0) {
                                FPx = t101;
                                FPy = t102;
                            } else {
                                FPx = t98;
                                FPy = t99;
                            }
                        }
                    }
                }
            }
        }
    } else {
        if (t6 <= 0.0) {
            if (0.0 >= t7) {
                if (0.0 >= 1.0) {
                    if (t73 > 1.0) {
                        if (FTy >= 0.0) {
                            FPx = t87;
                            FPy = t88;
                        } else {
                            FPx = t85;
                            FPy = t86;
                        }
                    } else {
                        if (-1.0 > t73) {
                            if (FTy >= 0.0) {
                                FPx = t83;
                                FPy = t84;
                            } else {
                                FPx = t81;
                                FPy = t82;
                            }
                        } else {
                            if (FTy >= 0.0) {
                                FPx = cos(t80) * t78 + FPx;
                                FPy = sin(t80) * t79 + FPy;
                            } else {
                                FPx = cos(t75) * t78 + FPx;
                                FPy = sin(t75) * t79 + FPy;
                            }
                        }
                    }
                } else {
                    if (t4 > 1.0) {
                        if (FTy >= 0.0) {
                            FPx = t43;
                            FPy = t45;
                        } else {
                            FPx = t38;
                            FPy = t40;
                        }
                    } else {
                        if (-1.0 > t4) {
                            if (FTy >= 0.0) {
                                FPx = t32;
                                FPy = t34;
                            } else {
                                FPx = t27;
                                FPy = t29;
                            }
                        } else {
                            if (FTy >= 0.0) {
                                FPx = t22;
                                FPy = t23;
                            } else {
                                FPx = t18;
                                FPy = t20;
                            }
                        }
                    }
                }
            } else {
                if (t63 >= 1.0) {
                    if (t64 > 1.0) {
                        if (FTy >= 0.0) {
                            FPx = t42 * t69 + FPx;
                            FPy = t44 * t70 + FPy;
                        } else {
                            FPx = t37 * t69 + FPx;
                            FPy = t39 * t70 + FPy;
                        }
                    } else {
                        if (-1.0 > t64) {
                            if (FTy >= 0.0) {
                                FPx = t31 * t69 + FPx;
                                FPy = t33 * t70 + FPy;
                            } else {
                                FPx = t26 * t69 + FPx;
                                FPy = t28 * t70 + FPy;
                            }
                        } else {
                            if (FTy >= 0.0) {
                                FPx = cos(t71) * t69 + FPx;
                                FPy = sin(t71) * t70 + FPy;
                            } else {
                                FPx = cos(t66) * t69 + FPx;
                                FPy = sin(t66) * t70 + FPy;
                            }
                        }
                    }
                } else {
                    if (t4 > 1.0) {
                        if (FTy >= 0.0) {
                            FPx = t43;
                            FPy = t45;
                        } else {
                            FPx = t38;
                            FPy = t40;
                        }
                    } else {
                        if (-1.0 > t4) {
                            if (FTy >= 0.0) {
                                FPx = t32;
                                FPy = t34;
                            } else {
                                FPx = t27;
                                FPy = t29;
                            }
                        } else {
                            if (FTy >= 0.0) {
                                FPx = t22;
                                FPy = t23;
                            } else {
                                FPx = t18;
                                FPy = t20;
                            }
                        }
                    }
                }
            }
        } else {
            if (0.0 >= t7) {
                if (t54 >= 1.0) {
                    if (t55 > 1.0) {
                        if (FTy >= 0.0) {
                            FPx = t42 * t60 + FPx;
                            FPy = t44 * t61 + FPy;
                        } else {
                            FPx = t37 * t60 + FPx;
                            FPy = t39 * t61 + FPy;
                        }
                    } else {
                        if (-1.0 > t55) {
                            if (FTy >= 0.0) {
                                FPx = t31 * t60 + FPx;
                                FPy = t33 * t61 + FPy;
                            } else {
                                FPx = t26 * t60 + FPx;
                                FPy = t28 * t61 + FPy;
                            }
                        } else {
                            if (FTy >= 0.0) {
                                FPx = cos(t62) * t60 + FPx;
                                FPy = sin(t62) * t61 + FPy;
                            } else {
                                FPx = cos(t57) * t60 + FPx;
                                FPy = sin(t57) * t61 + FPy;
                            }
                        }
                    }
                } else {
                    if (t4 > 1.0) {
                        if (FTy >= 0.0) {
                            FPx = t43;
                            FPy = t45;
                        } else {
                            FPx = t38;
                            FPy = t40;
                        }
                    } else {
                        if (-1.0 > t4) {
                            if (FTy >= 0.0) {
                                FPx = t32;
                                FPy = t34;
                            } else {
                                FPx = t27;
                                FPy = t29;
                            }
                        } else {
                            if (FTy >= 0.0) {
                                FPx = t22;
                                FPy = t23;
                            } else {
                                FPx = t18;
                                FPy = t20;
                            }
                        }
                    }
                }
            } else {
                if (t10 >= 1.0) {
                    if (t46 > 1.0) {
                        if (FTy >= 0.0) {
                            FPx = t42 * t51 + FPx;
                            FPy = t44 * t52 + FPy;
                        } else {
                            FPx = t37 * t51 + FPx;
                            FPy = t39 * t52 + FPy;
                        }
                    } else {
                        if (-1.0 > t46) {
                            if (FTy >= 0.0) {
                                FPx = t31 * t51 + FPx;
                                FPy = t33 * t52 + FPy;
                            } else {
                                FPx = t26 * t51 + FPx;
                                FPy = t28 * t52 + FPy;
                            }
                        } else {
                            if (FTy >= 0.0) {
                                FPx = cos(t53) * t51 + FPx;
                                FPy = sin(t53) * t52 + FPy;
                            } else {
                                FPx = cos(t48) * t51 + FPx;
                                FPy = sin(t48) * t52 + FPy;
                            }
                        }
                    }
                } else {
                    if (t4 > 1.0) {
                        if (FTy >= 0.0) {
                            FPx = t43;
                            FPy = t45;
                        } else {
                            FPx = t38;
                            FPy = t40;
                        }
                    } else {
                        if (-1.0 > t4) {
                            if (FTy >= 0.0) {
                                FPx = t32;
                                FPy = t34;
                            } else {
                                FPx = t27;
                                FPy = t29;
                            }
                        } else {
                            if (FTy >= 0.0) {
                                FPx = t22;
                                FPy = t23;
                            } else {
                                FPx = t18;
                                FPy = t20;
                            }
                        }
                    }
                }
            }
        }
    }
    return TRUE;
}