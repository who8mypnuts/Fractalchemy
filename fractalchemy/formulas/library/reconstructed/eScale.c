/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        eScale.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from eScale.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double eScale_scale;
    double eScale_angle;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("eScale");
APO_VARIABLES(
    VAR_REAL(eScale_scale, 1.0),
    VAR_REAL_CYCLE(eScale_angle, 0.0, M_2PI, 0.0)
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
    double t9 = M_2PI * VAR(eScale_scale);
    double t10 = M_PI * VAR(eScale_scale);
    double t11 = fmod((fmod((-t8 + VAR(eScale_angle) + M_PI) * VAR(eScale_scale), t9) - VAR(eScale_angle)) - t10, 1413754136);
    double t12 = t11 - M_2PI;
    double t13 = t12 + M_2PI;
    double t14 = exp(acosh(1.0) * VAR(eScale_scale));
    double t15 = 1.0 / t14;
    double t16 = 0.5 * (t15 + t14) * VVAR;
    double t17 = cos(t13) * t16 + FPx;
    double t18 = 0.5 * (t14 - t15) * VVAR;
    double t19 = sin(t13) * t18 + FPy;
    double t20 = cos(t12) * t16 + FPx;
    double t21 = sin(t12) * t18 + FPy;
    double t22 = t11 + M_2PI;
    double t23 = cos(t22) * t16 + FPx;
    double t24 = sin(t22) * t18 + FPy;
    double t25 = cos(t11) * t16 + FPx;
    double t26 = sin(t11) * t18 + FPy;
    double t27 = fmod((fmod((t8 + VAR(eScale_angle) + M_PI) * VAR(eScale_scale), t9) - VAR(eScale_angle)) - t10, 1413754136);
    double t28 = t27 - M_2PI;
    double t29 = t28 + M_2PI;
    double t30 = cos(t29) * t16 + FPx;
    double t31 = sin(t29) * t18 + FPy;
    double t32 = cos(t28) * t16 + FPx;
    double t33 = sin(t28) * t18 + FPy;
    double t34 = t27 + M_2PI;
    double t35 = cos(t34) * t16 + FPx;
    double t36 = sin(t34) * t18 + FPy;
    double t37 = cos(t27) * t16 + FPx;
    double t38 = sin(t27) * t18 + FPy;
    double t39 = acos(-1.0);
    double t40 = fmod((fmod((-t39 + VAR(eScale_angle) + M_PI) * VAR(eScale_scale), t9) - VAR(eScale_angle)) - t10, 1413754136);
    double t41 = t40 - M_2PI;
    double t42 = t41 + M_2PI;
    double t43 = cos(t42);
    double t44 = t43 * t16 + FPx;
    double t45 = sin(t42);
    double t46 = t45 * t18 + FPy;
    double t47 = cos(t41);
    double t48 = t47 * t16 + FPx;
    double t49 = sin(t41);
    double t50 = t49 * t18 + FPy;
    double t51 = t40 + M_2PI;
    double t52 = cos(t51);
    double t53 = t52 * t16 + FPx;
    double t54 = sin(t51);
    double t55 = t54 * t18 + FPy;
    double t56 = cos(t40);
    double t57 = t56 * t16 + FPx;
    double t58 = sin(t40);
    double t59 = t58 * t18 + FPy;
    double t60 = fmod((fmod((t39 + VAR(eScale_angle) + M_PI) * VAR(eScale_scale), t9) - VAR(eScale_angle)) - t10, 1413754136);
    double t61 = t60 - M_2PI;
    double t62 = t61 + M_2PI;
    double t63 = cos(t62);
    double t64 = t63 * t16 + FPx;
    double t65 = sin(t62);
    double t66 = t65 * t18 + FPy;
    double t67 = cos(t61);
    double t68 = t67 * t16 + FPx;
    double t69 = sin(t61);
    double t70 = t69 * t18 + FPy;
    double t71 = t60 + M_2PI;
    double t72 = cos(t71);
    double t73 = t72 * t16 + FPx;
    double t74 = sin(t71);
    double t75 = t74 * t18 + FPy;
    double t76 = cos(t60);
    double t77 = t76 * t16 + FPx;
    double t78 = sin(t60);
    double t79 = t78 * t18 + FPy;
    double t80 = acos(1.0);
    double t81 = fmod((fmod((-t80 + VAR(eScale_angle) + M_PI) * VAR(eScale_scale), t9) - VAR(eScale_angle)) - t10, 1413754136);
    double t82 = t81 - M_2PI;
    double t83 = t82 + M_2PI;
    double t84 = cos(t83);
    double t85 = t84 * t16 + FPx;
    double t86 = sin(t83);
    double t87 = t86 * t18 + FPy;
    double t88 = cos(t82);
    double t89 = t88 * t16 + FPx;
    double t90 = sin(t82);
    double t91 = t90 * t18 + FPy;
    double t92 = t81 + M_2PI;
    double t93 = cos(t92);
    double t94 = t93 * t16 + FPx;
    double t95 = sin(t92);
    double t96 = t95 * t18 + FPy;
    double t97 = cos(t81);
    double t98 = t97 * t16 + FPx;
    double t99 = sin(t81);
    double t100 = t99 * t18 + FPy;
    double t101 = fmod((fmod((t80 + VAR(eScale_angle) + M_PI) * VAR(eScale_scale), t9) - VAR(eScale_angle)) - t10, 1413754136);
    double t102 = t101 - M_2PI;
    double t103 = t102 + M_2PI;
    double t104 = cos(t103);
    double t105 = t104 * t16 + FPx;
    double t106 = sin(t103);
    double t107 = t106 * t18 + FPy;
    double t108 = cos(t102);
    double t109 = t108 * t16 + FPx;
    double t110 = sin(t102);
    double t111 = t110 * t18 + FPy;
    double t112 = t101 + M_2PI;
    double t113 = cos(t112);
    double t114 = t113 * t16 + FPx;
    double t115 = sin(t112);
    double t116 = t115 * t18 + FPy;
    double t117 = cos(t101);
    double t118 = t117 * t16 + FPx;
    double t119 = sin(t101);
    double t120 = t119 * t18 + FPy;
    double t121 = (1.0 / t7) * FTx;
    double t122 = acos(t121);
    double t123 = fmod((fmod((-t122 + VAR(eScale_angle) + M_PI) * VAR(eScale_scale), t9) - VAR(eScale_angle)) - t10, 1413754136);
    double t124 = t123 - M_2PI;
    double t125 = t124 + M_2PI;
    double t126 = exp(acosh(t7) * VAR(eScale_scale));
    double t127 = 1.0 / t126;
    double t128 = 0.5 * (t127 + t126) * VVAR;
    double t129 = 0.5 * (t126 - t127) * VVAR;
    double t130 = t123 + M_2PI;
    double t131 = fmod((fmod((t122 + VAR(eScale_angle) + M_PI) * VAR(eScale_scale), t9) - VAR(eScale_angle)) - t10, 1413754136);
    double t132 = t131 - M_2PI;
    double t133 = t132 + M_2PI;
    double t134 = t131 + M_2PI;
    double t135 = 0.5 * t5;
    double t136 = (1.0 / t135) * FTx;
    double t137 = acos(t136);
    double t138 = fmod((fmod((-t137 + VAR(eScale_angle) + M_PI) * VAR(eScale_scale), t9) - VAR(eScale_angle)) - t10, 1413754136);
    double t139 = t138 - M_2PI;
    double t140 = t139 + M_2PI;
    double t141 = exp(acosh(t135) * VAR(eScale_scale));
    double t142 = 1.0 / t141;
    double t143 = 0.5 * (t142 + t141) * VVAR;
    double t144 = 0.5 * (t141 - t142) * VVAR;
    double t145 = t138 + M_2PI;
    double t146 = fmod((fmod((t137 + VAR(eScale_angle) + M_PI) * VAR(eScale_scale), t9) - VAR(eScale_angle)) - t10, 1413754136);
    double t147 = t146 - M_2PI;
    double t148 = t147 + M_2PI;
    double t149 = t146 + M_2PI;
    double t150 = 0.5 * t6;
    double t151 = (1.0 / t150) * FTx;
    double t152 = acos(t151);
    double t153 = fmod((fmod((-t152 + VAR(eScale_angle) + M_PI) * VAR(eScale_scale), t9) - VAR(eScale_angle)) - t10, 1413754136);
    double t154 = t153 - M_2PI;
    double t155 = t154 + M_2PI;
    double t156 = exp(acosh(t150) * VAR(eScale_scale));
    double t157 = 1.0 / t156;
    double t158 = 0.5 * (t157 + t156) * VVAR;
    double t159 = 0.5 * (t156 - t157) * VVAR;
    double t160 = t153 + M_2PI;
    double t161 = fmod((fmod((t152 + VAR(eScale_angle) + M_PI) * VAR(eScale_scale), t9) - VAR(eScale_angle)) - t10, 1413754136);
    double t162 = t161 - M_2PI;
    double t163 = t162 + M_2PI;
    double t164 = t161 + M_2PI;
    double t165 = (1.0 / 0.0) * FTx;
    double t166 = acos(t165);
    double t167 = fmod((fmod((-t166 + VAR(eScale_angle) + M_PI) * VAR(eScale_scale), t9) - VAR(eScale_angle)) - t10, 1413754136);
    double t168 = t167 - M_2PI;
    double t169 = t168 + M_2PI;
    double t170 = exp(acosh(0.0) * VAR(eScale_scale));
    double t171 = 1.0 / t170;
    double t172 = 0.5 * (t171 + t170) * VVAR;
    double t173 = 0.5 * (t170 - t171) * VVAR;
    double t174 = t167 + M_2PI;
    double t175 = fmod((fmod((t166 + VAR(eScale_angle) + M_PI) * VAR(eScale_scale), t9) - VAR(eScale_angle)) - t10, 1413754136);
    double t176 = t175 - M_2PI;
    double t177 = t176 + M_2PI;
    double t178 = t175 + M_2PI;
    if (t3 <= 0.0) {
        if (0.0 >= t4) {
            if (0.0 >= 1.0) {
                if (t165 > 1.0) {
                    if (FTy >= 0.0) {
                        if (t101 <= M_PI) {
                            if (t101 >= -M_PI) {
                                FPx = t117 * t172 + FPx;
                                FPy = t119 * t173 + FPy;
                            } else {
                                FPx = t113 * t172 + FPx;
                                FPy = t115 * t173 + FPy;
                            }
                        } else {
                            if (t102 >= -M_PI) {
                                FPx = t108 * t172 + FPx;
                                FPy = t110 * t173 + FPy;
                            } else {
                                FPx = t104 * t172 + FPx;
                                FPy = t106 * t173 + FPy;
                            }
                        }
                    } else {
                        if (t81 <= M_PI) {
                            if (t81 >= -M_PI) {
                                FPx = t97 * t172 + FPx;
                                FPy = t99 * t173 + FPy;
                            } else {
                                FPx = t93 * t172 + FPx;
                                FPy = t95 * t173 + FPy;
                            }
                        } else {
                            if (t82 >= -M_PI) {
                                FPx = t88 * t172 + FPx;
                                FPy = t90 * t173 + FPy;
                            } else {
                                FPx = t84 * t172 + FPx;
                                FPy = t86 * t173 + FPy;
                            }
                        }
                    }
                } else {
                    if (-1.0 > t165) {
                        if (FTy >= 0.0) {
                            if (t60 <= M_PI) {
                                if (t60 >= -M_PI) {
                                    FPx = t76 * t172 + FPx;
                                    FPy = t78 * t173 + FPy;
                                } else {
                                    FPx = t72 * t172 + FPx;
                                    FPy = t74 * t173 + FPy;
                                }
                            } else {
                                if (t61 >= -M_PI) {
                                    FPx = t67 * t172 + FPx;
                                    FPy = t69 * t173 + FPy;
                                } else {
                                    FPx = t63 * t172 + FPx;
                                    FPy = t65 * t173 + FPy;
                                }
                            }
                        } else {
                            if (t40 <= M_PI) {
                                if (t40 >= -M_PI) {
                                    FPx = t56 * t172 + FPx;
                                    FPy = t58 * t173 + FPy;
                                } else {
                                    FPx = t52 * t172 + FPx;
                                    FPy = t54 * t173 + FPy;
                                }
                            } else {
                                if (t41 >= -M_PI) {
                                    FPx = t47 * t172 + FPx;
                                    FPy = t49 * t173 + FPy;
                                } else {
                                    FPx = t43 * t172 + FPx;
                                    FPy = t45 * t173 + FPy;
                                }
                            }
                        }
                    } else {
                        if (FTy >= 0.0) {
                            if (t175 <= M_PI) {
                                if (t175 >= -M_PI) {
                                    FPx = cos(t175) * t172 + FPx;
                                    FPy = sin(t175) * t173 + FPy;
                                } else {
                                    FPx = cos(t178) * t172 + FPx;
                                    FPy = sin(t178) * t173 + FPy;
                                }
                            } else {
                                if (t176 >= -M_PI) {
                                    FPx = cos(t176) * t172 + FPx;
                                    FPy = sin(t176) * t173 + FPy;
                                } else {
                                    FPx = cos(t177) * t172 + FPx;
                                    FPy = sin(t177) * t173 + FPy;
                                }
                            }
                        } else {
                            if (t167 <= M_PI) {
                                if (t167 >= -M_PI) {
                                    FPx = cos(t167) * t172 + FPx;
                                    FPy = sin(t167) * t173 + FPy;
                                } else {
                                    FPx = cos(t174) * t172 + FPx;
                                    FPy = sin(t174) * t173 + FPy;
                                }
                            } else {
                                if (t168 >= -M_PI) {
                                    FPx = cos(t168) * t172 + FPx;
                                    FPy = sin(t168) * t173 + FPy;
                                } else {
                                    FPx = cos(t169) * t172 + FPx;
                                    FPy = sin(t169) * t173 + FPy;
                                }
                            }
                        }
                    }
                }
            } else {
                if (FTx > 1.0) {
                    if (FTy >= 0.0) {
                        if (t101 <= M_PI) {
                            if (t101 >= -M_PI) {
                                FPx = t118;
                                FPy = t120;
                            } else {
                                FPx = t114;
                                FPy = t116;
                            }
                        } else {
                            if (t102 >= -M_PI) {
                                FPx = t109;
                                FPy = t111;
                            } else {
                                FPx = t105;
                                FPy = t107;
                            }
                        }
                    } else {
                        if (t81 <= M_PI) {
                            if (t81 >= -M_PI) {
                                FPx = t98;
                                FPy = t100;
                            } else {
                                FPx = t94;
                                FPy = t96;
                            }
                        } else {
                            if (t82 >= -M_PI) {
                                FPx = t89;
                                FPy = t91;
                            } else {
                                FPx = t85;
                                FPy = t87;
                            }
                        }
                    }
                } else {
                    if (-1.0 > FTx) {
                        if (FTy >= 0.0) {
                            if (t60 <= M_PI) {
                                if (t60 >= -M_PI) {
                                    FPx = t77;
                                    FPy = t79;
                                } else {
                                    FPx = t73;
                                    FPy = t75;
                                }
                            } else {
                                if (t61 >= -M_PI) {
                                    FPx = t68;
                                    FPy = t70;
                                } else {
                                    FPx = t64;
                                    FPy = t66;
                                }
                            }
                        } else {
                            if (t40 <= M_PI) {
                                if (t40 >= -M_PI) {
                                    FPx = t57;
                                    FPy = t59;
                                } else {
                                    FPx = t53;
                                    FPy = t55;
                                }
                            } else {
                                if (t41 >= -M_PI) {
                                    FPx = t48;
                                    FPy = t50;
                                } else {
                                    FPx = t44;
                                    FPy = t46;
                                }
                            }
                        }
                    } else {
                        if (FTy >= 0.0) {
                            if (t27 <= M_PI) {
                                if (t27 >= -M_PI) {
                                    FPx = t37;
                                    FPy = t38;
                                } else {
                                    FPx = t35;
                                    FPy = t36;
                                }
                            } else {
                                if (t28 >= -M_PI) {
                                    FPx = t32;
                                    FPy = t33;
                                } else {
                                    FPx = t30;
                                    FPy = t31;
                                }
                            }
                        } else {
                            if (t11 <= M_PI) {
                                if (t11 >= -M_PI) {
                                    FPx = t25;
                                    FPy = t26;
                                } else {
                                    FPx = t23;
                                    FPy = t24;
                                }
                            } else {
                                if (t12 >= -M_PI) {
                                    FPx = t20;
                                    FPy = t21;
                                } else {
                                    FPx = t17;
                                    FPy = t19;
                                }
                            }
                        }
                    }
                }
            }
        } else {
            if (t150 >= 1.0) {
                if (t151 > 1.0) {
                    if (FTy >= 0.0) {
                        if (t101 <= M_PI) {
                            if (t101 >= -M_PI) {
                                FPx = t117 * t158 + FPx;
                                FPy = t119 * t159 + FPy;
                            } else {
                                FPx = t113 * t158 + FPx;
                                FPy = t115 * t159 + FPy;
                            }
                        } else {
                            if (t102 >= -M_PI) {
                                FPx = t108 * t158 + FPx;
                                FPy = t110 * t159 + FPy;
                            } else {
                                FPx = t104 * t158 + FPx;
                                FPy = t106 * t159 + FPy;
                            }
                        }
                    } else {
                        if (t81 <= M_PI) {
                            if (t81 >= -M_PI) {
                                FPx = t97 * t158 + FPx;
                                FPy = t99 * t159 + FPy;
                            } else {
                                FPx = t93 * t158 + FPx;
                                FPy = t95 * t159 + FPy;
                            }
                        } else {
                            if (t82 >= -M_PI) {
                                FPx = t88 * t158 + FPx;
                                FPy = t90 * t159 + FPy;
                            } else {
                                FPx = t84 * t158 + FPx;
                                FPy = t86 * t159 + FPy;
                            }
                        }
                    }
                } else {
                    if (-1.0 > t151) {
                        if (FTy >= 0.0) {
                            if (t60 <= M_PI) {
                                if (t60 >= -M_PI) {
                                    FPx = t76 * t158 + FPx;
                                    FPy = t78 * t159 + FPy;
                                } else {
                                    FPx = t72 * t158 + FPx;
                                    FPy = t74 * t159 + FPy;
                                }
                            } else {
                                if (t61 >= -M_PI) {
                                    FPx = t67 * t158 + FPx;
                                    FPy = t69 * t159 + FPy;
                                } else {
                                    FPx = t63 * t158 + FPx;
                                    FPy = t65 * t159 + FPy;
                                }
                            }
                        } else {
                            if (t40 <= M_PI) {
                                if (t40 >= -M_PI) {
                                    FPx = t56 * t158 + FPx;
                                    FPy = t58 * t159 + FPy;
                                } else {
                                    FPx = t52 * t158 + FPx;
                                    FPy = t54 * t159 + FPy;
                                }
                            } else {
                                if (t41 >= -M_PI) {
                                    FPx = t47 * t158 + FPx;
                                    FPy = t49 * t159 + FPy;
                                } else {
                                    FPx = t43 * t158 + FPx;
                                    FPy = t45 * t159 + FPy;
                                }
                            }
                        }
                    } else {
                        if (FTy >= 0.0) {
                            if (t161 <= M_PI) {
                                if (t161 >= -M_PI) {
                                    FPx = cos(t161) * t158 + FPx;
                                    FPy = sin(t161) * t159 + FPy;
                                } else {
                                    FPx = cos(t164) * t158 + FPx;
                                    FPy = sin(t164) * t159 + FPy;
                                }
                            } else {
                                if (t162 >= -M_PI) {
                                    FPx = cos(t162) * t158 + FPx;
                                    FPy = sin(t162) * t159 + FPy;
                                } else {
                                    FPx = cos(t163) * t158 + FPx;
                                    FPy = sin(t163) * t159 + FPy;
                                }
                            }
                        } else {
                            if (t153 <= M_PI) {
                                if (t153 >= -M_PI) {
                                    FPx = cos(t153) * t158 + FPx;
                                    FPy = sin(t153) * t159 + FPy;
                                } else {
                                    FPx = cos(t160) * t158 + FPx;
                                    FPy = sin(t160) * t159 + FPy;
                                }
                            } else {
                                if (t154 >= -M_PI) {
                                    FPx = cos(t154) * t158 + FPx;
                                    FPy = sin(t154) * t159 + FPy;
                                } else {
                                    FPx = cos(t155) * t158 + FPx;
                                    FPy = sin(t155) * t159 + FPy;
                                }
                            }
                        }
                    }
                }
            } else {
                if (FTx > 1.0) {
                    if (FTy >= 0.0) {
                        if (t101 <= M_PI) {
                            if (t101 >= -M_PI) {
                                FPx = t118;
                                FPy = t120;
                            } else {
                                FPx = t114;
                                FPy = t116;
                            }
                        } else {
                            if (t102 >= -M_PI) {
                                FPx = t109;
                                FPy = t111;
                            } else {
                                FPx = t105;
                                FPy = t107;
                            }
                        }
                    } else {
                        if (t81 <= M_PI) {
                            if (t81 >= -M_PI) {
                                FPx = t98;
                                FPy = t100;
                            } else {
                                FPx = t94;
                                FPy = t96;
                            }
                        } else {
                            if (t82 >= -M_PI) {
                                FPx = t89;
                                FPy = t91;
                            } else {
                                FPx = t85;
                                FPy = t87;
                            }
                        }
                    }
                } else {
                    if (-1.0 > FTx) {
                        if (FTy >= 0.0) {
                            if (t60 <= M_PI) {
                                if (t60 >= -M_PI) {
                                    FPx = t77;
                                    FPy = t79;
                                } else {
                                    FPx = t73;
                                    FPy = t75;
                                }
                            } else {
                                if (t61 >= -M_PI) {
                                    FPx = t68;
                                    FPy = t70;
                                } else {
                                    FPx = t64;
                                    FPy = t66;
                                }
                            }
                        } else {
                            if (t40 <= M_PI) {
                                if (t40 >= -M_PI) {
                                    FPx = t57;
                                    FPy = t59;
                                } else {
                                    FPx = t53;
                                    FPy = t55;
                                }
                            } else {
                                if (t41 >= -M_PI) {
                                    FPx = t48;
                                    FPy = t50;
                                } else {
                                    FPx = t44;
                                    FPy = t46;
                                }
                            }
                        }
                    } else {
                        if (FTy >= 0.0) {
                            if (t27 <= M_PI) {
                                if (t27 >= -M_PI) {
                                    FPx = t37;
                                    FPy = t38;
                                } else {
                                    FPx = t35;
                                    FPy = t36;
                                }
                            } else {
                                if (t28 >= -M_PI) {
                                    FPx = t32;
                                    FPy = t33;
                                } else {
                                    FPx = t30;
                                    FPy = t31;
                                }
                            }
                        } else {
                            if (t11 <= M_PI) {
                                if (t11 >= -M_PI) {
                                    FPx = t25;
                                    FPy = t26;
                                } else {
                                    FPx = t23;
                                    FPy = t24;
                                }
                            } else {
                                if (t12 >= -M_PI) {
                                    FPx = t20;
                                    FPy = t21;
                                } else {
                                    FPx = t17;
                                    FPy = t19;
                                }
                            }
                        }
                    }
                }
            }
        }
    } else {
        if (0.0 >= t4) {
            if (t135 >= 1.0) {
                if (t136 > 1.0) {
                    if (FTy >= 0.0) {
                        if (t101 <= M_PI) {
                            if (t101 >= -M_PI) {
                                FPx = t117 * t143 + FPx;
                                FPy = t119 * t144 + FPy;
                            } else {
                                FPx = t113 * t143 + FPx;
                                FPy = t115 * t144 + FPy;
                            }
                        } else {
                            if (t102 >= -M_PI) {
                                FPx = t108 * t143 + FPx;
                                FPy = t110 * t144 + FPy;
                            } else {
                                FPx = t104 * t143 + FPx;
                                FPy = t106 * t144 + FPy;
                            }
                        }
                    } else {
                        if (t81 <= M_PI) {
                            if (t81 >= -M_PI) {
                                FPx = t97 * t143 + FPx;
                                FPy = t99 * t144 + FPy;
                            } else {
                                FPx = t93 * t143 + FPx;
                                FPy = t95 * t144 + FPy;
                            }
                        } else {
                            if (t82 >= -M_PI) {
                                FPx = t88 * t143 + FPx;
                                FPy = t90 * t144 + FPy;
                            } else {
                                FPx = t84 * t143 + FPx;
                                FPy = t86 * t144 + FPy;
                            }
                        }
                    }
                } else {
                    if (-1.0 > t136) {
                        if (FTy >= 0.0) {
                            if (t60 <= M_PI) {
                                if (t60 >= -M_PI) {
                                    FPx = t76 * t143 + FPx;
                                    FPy = t78 * t144 + FPy;
                                } else {
                                    FPx = t72 * t143 + FPx;
                                    FPy = t74 * t144 + FPy;
                                }
                            } else {
                                if (t61 >= -M_PI) {
                                    FPx = t67 * t143 + FPx;
                                    FPy = t69 * t144 + FPy;
                                } else {
                                    FPx = t63 * t143 + FPx;
                                    FPy = t65 * t144 + FPy;
                                }
                            }
                        } else {
                            if (t40 <= M_PI) {
                                if (t40 >= -M_PI) {
                                    FPx = t56 * t143 + FPx;
                                    FPy = t58 * t144 + FPy;
                                } else {
                                    FPx = t52 * t143 + FPx;
                                    FPy = t54 * t144 + FPy;
                                }
                            } else {
                                if (t41 >= -M_PI) {
                                    FPx = t47 * t143 + FPx;
                                    FPy = t49 * t144 + FPy;
                                } else {
                                    FPx = t43 * t143 + FPx;
                                    FPy = t45 * t144 + FPy;
                                }
                            }
                        }
                    } else {
                        if (FTy >= 0.0) {
                            if (t146 <= M_PI) {
                                if (t146 >= -M_PI) {
                                    FPx = cos(t146) * t143 + FPx;
                                    FPy = sin(t146) * t144 + FPy;
                                } else {
                                    FPx = cos(t149) * t143 + FPx;
                                    FPy = sin(t149) * t144 + FPy;
                                }
                            } else {
                                if (t147 >= -M_PI) {
                                    FPx = cos(t147) * t143 + FPx;
                                    FPy = sin(t147) * t144 + FPy;
                                } else {
                                    FPx = cos(t148) * t143 + FPx;
                                    FPy = sin(t148) * t144 + FPy;
                                }
                            }
                        } else {
                            if (t138 <= M_PI) {
                                if (t138 >= -M_PI) {
                                    FPx = cos(t138) * t143 + FPx;
                                    FPy = sin(t138) * t144 + FPy;
                                } else {
                                    FPx = cos(t145) * t143 + FPx;
                                    FPy = sin(t145) * t144 + FPy;
                                }
                            } else {
                                if (t139 >= -M_PI) {
                                    FPx = cos(t139) * t143 + FPx;
                                    FPy = sin(t139) * t144 + FPy;
                                } else {
                                    FPx = cos(t140) * t143 + FPx;
                                    FPy = sin(t140) * t144 + FPy;
                                }
                            }
                        }
                    }
                }
            } else {
                if (FTx > 1.0) {
                    if (FTy >= 0.0) {
                        if (t101 <= M_PI) {
                            if (t101 >= -M_PI) {
                                FPx = t118;
                                FPy = t120;
                            } else {
                                FPx = t114;
                                FPy = t116;
                            }
                        } else {
                            if (t102 >= -M_PI) {
                                FPx = t109;
                                FPy = t111;
                            } else {
                                FPx = t105;
                                FPy = t107;
                            }
                        }
                    } else {
                        if (t81 <= M_PI) {
                            if (t81 >= -M_PI) {
                                FPx = t98;
                                FPy = t100;
                            } else {
                                FPx = t94;
                                FPy = t96;
                            }
                        } else {
                            if (t82 >= -M_PI) {
                                FPx = t89;
                                FPy = t91;
                            } else {
                                FPx = t85;
                                FPy = t87;
                            }
                        }
                    }
                } else {
                    if (-1.0 > FTx) {
                        if (FTy >= 0.0) {
                            if (t60 <= M_PI) {
                                if (t60 >= -M_PI) {
                                    FPx = t77;
                                    FPy = t79;
                                } else {
                                    FPx = t73;
                                    FPy = t75;
                                }
                            } else {
                                if (t61 >= -M_PI) {
                                    FPx = t68;
                                    FPy = t70;
                                } else {
                                    FPx = t64;
                                    FPy = t66;
                                }
                            }
                        } else {
                            if (t40 <= M_PI) {
                                if (t40 >= -M_PI) {
                                    FPx = t57;
                                    FPy = t59;
                                } else {
                                    FPx = t53;
                                    FPy = t55;
                                }
                            } else {
                                if (t41 >= -M_PI) {
                                    FPx = t48;
                                    FPy = t50;
                                } else {
                                    FPx = t44;
                                    FPy = t46;
                                }
                            }
                        }
                    } else {
                        if (FTy >= 0.0) {
                            if (t27 <= M_PI) {
                                if (t27 >= -M_PI) {
                                    FPx = t37;
                                    FPy = t38;
                                } else {
                                    FPx = t35;
                                    FPy = t36;
                                }
                            } else {
                                if (t28 >= -M_PI) {
                                    FPx = t32;
                                    FPy = t33;
                                } else {
                                    FPx = t30;
                                    FPy = t31;
                                }
                            }
                        } else {
                            if (t11 <= M_PI) {
                                if (t11 >= -M_PI) {
                                    FPx = t25;
                                    FPy = t26;
                                } else {
                                    FPx = t23;
                                    FPy = t24;
                                }
                            } else {
                                if (t12 >= -M_PI) {
                                    FPx = t20;
                                    FPy = t21;
                                } else {
                                    FPx = t17;
                                    FPy = t19;
                                }
                            }
                        }
                    }
                }
            }
        } else {
            if (t7 >= 1.0) {
                if (t121 > 1.0) {
                    if (FTy >= 0.0) {
                        if (t101 <= M_PI) {
                            if (t101 >= -M_PI) {
                                FPx = t117 * t128 + FPx;
                                FPy = t119 * t129 + FPy;
                            } else {
                                FPx = t113 * t128 + FPx;
                                FPy = t115 * t129 + FPy;
                            }
                        } else {
                            if (t102 >= -M_PI) {
                                FPx = t108 * t128 + FPx;
                                FPy = t110 * t129 + FPy;
                            } else {
                                FPx = t104 * t128 + FPx;
                                FPy = t106 * t129 + FPy;
                            }
                        }
                    } else {
                        if (t81 <= M_PI) {
                            if (t81 >= -M_PI) {
                                FPx = t97 * t128 + FPx;
                                FPy = t99 * t129 + FPy;
                            } else {
                                FPx = t93 * t128 + FPx;
                                FPy = t95 * t129 + FPy;
                            }
                        } else {
                            if (t82 >= -M_PI) {
                                FPx = t88 * t128 + FPx;
                                FPy = t90 * t129 + FPy;
                            } else {
                                FPx = t84 * t128 + FPx;
                                FPy = t86 * t129 + FPy;
                            }
                        }
                    }
                } else {
                    if (-1.0 > t121) {
                        if (FTy >= 0.0) {
                            if (t60 <= M_PI) {
                                if (t60 >= -M_PI) {
                                    FPx = t76 * t128 + FPx;
                                    FPy = t78 * t129 + FPy;
                                } else {
                                    FPx = t72 * t128 + FPx;
                                    FPy = t74 * t129 + FPy;
                                }
                            } else {
                                if (t61 >= -M_PI) {
                                    FPx = t67 * t128 + FPx;
                                    FPy = t69 * t129 + FPy;
                                } else {
                                    FPx = t63 * t128 + FPx;
                                    FPy = t65 * t129 + FPy;
                                }
                            }
                        } else {
                            if (t40 <= M_PI) {
                                if (t40 >= -M_PI) {
                                    FPx = t56 * t128 + FPx;
                                    FPy = t58 * t129 + FPy;
                                } else {
                                    FPx = t52 * t128 + FPx;
                                    FPy = t54 * t129 + FPy;
                                }
                            } else {
                                if (t41 >= -M_PI) {
                                    FPx = t47 * t128 + FPx;
                                    FPy = t49 * t129 + FPy;
                                } else {
                                    FPx = t43 * t128 + FPx;
                                    FPy = t45 * t129 + FPy;
                                }
                            }
                        }
                    } else {
                        if (FTy >= 0.0) {
                            if (t131 <= M_PI) {
                                if (t131 >= -M_PI) {
                                    FPx = cos(t131) * t128 + FPx;
                                    FPy = sin(t131) * t129 + FPy;
                                } else {
                                    FPx = cos(t134) * t128 + FPx;
                                    FPy = sin(t134) * t129 + FPy;
                                }
                            } else {
                                if (t132 >= -M_PI) {
                                    FPx = cos(t132) * t128 + FPx;
                                    FPy = sin(t132) * t129 + FPy;
                                } else {
                                    FPx = cos(t133) * t128 + FPx;
                                    FPy = sin(t133) * t129 + FPy;
                                }
                            }
                        } else {
                            if (t123 <= M_PI) {
                                if (t123 >= -M_PI) {
                                    FPx = cos(t123) * t128 + FPx;
                                    FPy = sin(t123) * t129 + FPy;
                                } else {
                                    FPx = cos(t130) * t128 + FPx;
                                    FPy = sin(t130) * t129 + FPy;
                                }
                            } else {
                                if (t124 >= -M_PI) {
                                    FPx = cos(t124) * t128 + FPx;
                                    FPy = sin(t124) * t129 + FPy;
                                } else {
                                    FPx = cos(t125) * t128 + FPx;
                                    FPy = sin(t125) * t129 + FPy;
                                }
                            }
                        }
                    }
                }
            } else {
                if (FTx > 1.0) {
                    if (FTy >= 0.0) {
                        if (t101 <= M_PI) {
                            if (t101 >= -M_PI) {
                                FPx = t118;
                                FPy = t120;
                            } else {
                                FPx = t114;
                                FPy = t116;
                            }
                        } else {
                            if (t102 >= -M_PI) {
                                FPx = t109;
                                FPy = t111;
                            } else {
                                FPx = t105;
                                FPy = t107;
                            }
                        }
                    } else {
                        if (t81 <= M_PI) {
                            if (t81 >= -M_PI) {
                                FPx = t98;
                                FPy = t100;
                            } else {
                                FPx = t94;
                                FPy = t96;
                            }
                        } else {
                            if (t82 >= -M_PI) {
                                FPx = t89;
                                FPy = t91;
                            } else {
                                FPx = t85;
                                FPy = t87;
                            }
                        }
                    }
                } else {
                    if (-1.0 > FTx) {
                        if (FTy >= 0.0) {
                            if (t60 <= M_PI) {
                                if (t60 >= -M_PI) {
                                    FPx = t77;
                                    FPy = t79;
                                } else {
                                    FPx = t73;
                                    FPy = t75;
                                }
                            } else {
                                if (t61 >= -M_PI) {
                                    FPx = t68;
                                    FPy = t70;
                                } else {
                                    FPx = t64;
                                    FPy = t66;
                                }
                            }
                        } else {
                            if (t40 <= M_PI) {
                                if (t40 >= -M_PI) {
                                    FPx = t57;
                                    FPy = t59;
                                } else {
                                    FPx = t53;
                                    FPy = t55;
                                }
                            } else {
                                if (t41 >= -M_PI) {
                                    FPx = t48;
                                    FPy = t50;
                                } else {
                                    FPx = t44;
                                    FPy = t46;
                                }
                            }
                        }
                    } else {
                        if (FTy >= 0.0) {
                            if (t27 <= M_PI) {
                                if (t27 >= -M_PI) {
                                    FPx = t37;
                                    FPy = t38;
                                } else {
                                    FPx = t35;
                                    FPy = t36;
                                }
                            } else {
                                if (t28 >= -M_PI) {
                                    FPx = t32;
                                    FPy = t33;
                                } else {
                                    FPx = t30;
                                    FPy = t31;
                                }
                            }
                        } else {
                            if (t11 <= M_PI) {
                                if (t11 >= -M_PI) {
                                    FPx = t25;
                                    FPy = t26;
                                } else {
                                    FPx = t23;
                                    FPy = t24;
                                }
                            } else {
                                if (t12 >= -M_PI) {
                                    FPx = t20;
                                    FPy = t21;
                                } else {
                                    FPx = t17;
                                    FPy = t19;
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