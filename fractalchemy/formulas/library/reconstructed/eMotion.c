/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        eMotion.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from eMotion.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double eMotion_move;
    double eMotion_rotate;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("eMotion");
APO_VARIABLES(
    VAR_REAL(eMotion_move, 0.0),
    VAR_REAL_CYCLE(eMotion_rotate, 0.0, M_2PI, 0.0)
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
    double t9 = -t8;
    double t10 = acosh(1.0);
    double t11 = t10 + VAR(eMotion_move);
    double t12 = t8 + VAR(eMotion_rotate);
    double t13 = cos(t12);
    double t14 = exp(-t11);
    double t15 = 1.0 / t14;
    double t16 = 0.5 * (t15 + t14) * VVAR;
    double t17 = t13 * t16 + FPx;
    double t18 = sin(t12);
    double t19 = 0.5 * (t14 - t15) * VVAR;
    double t20 = t18 * t19 + FPy;
    double t21 = t9 + VAR(eMotion_rotate);
    double t22 = cos(t21);
    double t23 = exp(t11);
    double t24 = 1.0 / t23;
    double t25 = 0.5 * (t24 + t23) * VVAR;
    double t26 = t22 * t25 + FPx;
    double t27 = sin(t21);
    double t28 = 0.5 * (t23 - t24) * VVAR;
    double t29 = t27 * t28 + FPy;
    double t30 = t10 - VAR(eMotion_move);
    double t31 = exp(-t30);
    double t32 = 1.0 / t31;
    double t33 = 0.5 * (t32 + t31) * VVAR;
    double t34 = t13 * t33 + FPx;
    double t35 = 0.5 * (t31 - t32) * VVAR;
    double t36 = t18 * t35 + FPy;
    double t37 = exp(t30);
    double t38 = 1.0 / t37;
    double t39 = 0.5 * (t38 + t37) * VVAR;
    double t40 = t22 * t39 + FPx;
    double t41 = 0.5 * (t37 - t38) * VVAR;
    double t42 = t27 * t41 + FPy;
    double t43 = t22 * t16 + FPx;
    double t44 = t27 * t19 + FPy;
    double t45 = t13 * t25 + FPx;
    double t46 = t18 * t28 + FPy;
    double t47 = t22 * t33 + FPx;
    double t48 = t27 * t35 + FPy;
    double t49 = t13 * t39 + FPx;
    double t50 = t18 * t41 + FPy;
    double t51 = acos(-1.0);
    double t52 = -t51;
    double t53 = t51 + VAR(eMotion_rotate);
    double t54 = cos(t53);
    double t55 = t54 * t16 + FPx;
    double t56 = sin(t53);
    double t57 = t56 * t19 + FPy;
    double t58 = t52 + VAR(eMotion_rotate);
    double t59 = cos(t58);
    double t60 = t59 * t25 + FPx;
    double t61 = sin(t58);
    double t62 = t61 * t28 + FPy;
    double t63 = t54 * t33 + FPx;
    double t64 = t56 * t35 + FPy;
    double t65 = t59 * t39 + FPx;
    double t66 = t61 * t41 + FPy;
    double t67 = t59 * t16 + FPx;
    double t68 = t61 * t19 + FPy;
    double t69 = t54 * t25 + FPx;
    double t70 = t56 * t28 + FPy;
    double t71 = t59 * t33 + FPx;
    double t72 = t61 * t35 + FPy;
    double t73 = t54 * t39 + FPx;
    double t74 = t56 * t41 + FPy;
    double t75 = acos(1.0);
    double t76 = -t75;
    double t77 = t75 + VAR(eMotion_rotate);
    double t78 = cos(t77);
    double t79 = t78 * t16 + FPx;
    double t80 = sin(t77);
    double t81 = t80 * t19 + FPy;
    double t82 = t76 + VAR(eMotion_rotate);
    double t83 = cos(t82);
    double t84 = t83 * t25 + FPx;
    double t85 = sin(t82);
    double t86 = t85 * t28 + FPy;
    double t87 = t78 * t33 + FPx;
    double t88 = t80 * t35 + FPy;
    double t89 = t83 * t39 + FPx;
    double t90 = t85 * t41 + FPy;
    double t91 = t83 * t16 + FPx;
    double t92 = t85 * t19 + FPy;
    double t93 = t78 * t25 + FPx;
    double t94 = t80 * t28 + FPy;
    double t95 = t83 * t33 + FPx;
    double t96 = t85 * t35 + FPy;
    double t97 = t78 * t39 + FPx;
    double t98 = t80 * t41 + FPy;
    double t99 = (1.0 / t7) * FTx;
    double t100 = acos(t99);
    double t101 = -t100;
    double t102 = acosh(t7);
    double t103 = t102 + VAR(eMotion_move);
    double t104 = t100 + VAR(eMotion_rotate);
    double t105 = cos(t104);
    double t106 = exp(-t103);
    double t107 = 1.0 / t106;
    double t108 = 0.5 * (t107 + t106) * VVAR;
    double t109 = sin(t104);
    double t110 = 0.5 * (t106 - t107) * VVAR;
    double t111 = t101 + VAR(eMotion_rotate);
    double t112 = cos(t111);
    double t113 = exp(t103);
    double t114 = 1.0 / t113;
    double t115 = 0.5 * (t114 + t113) * VVAR;
    double t116 = sin(t111);
    double t117 = 0.5 * (t113 - t114) * VVAR;
    double t118 = t102 - VAR(eMotion_move);
    double t119 = exp(-t118);
    double t120 = 1.0 / t119;
    double t121 = 0.5 * (t120 + t119) * VVAR;
    double t122 = 0.5 * (t119 - t120) * VVAR;
    double t123 = exp(t118);
    double t124 = 1.0 / t123;
    double t125 = 0.5 * (t124 + t123) * VVAR;
    double t126 = 0.5 * (t123 - t124) * VVAR;
    double t127 = 0.5 * t5;
    double t128 = (1.0 / t127) * FTx;
    double t129 = acos(t128);
    double t130 = -t129;
    double t131 = acosh(t127);
    double t132 = t131 + VAR(eMotion_move);
    double t133 = t129 + VAR(eMotion_rotate);
    double t134 = cos(t133);
    double t135 = exp(-t132);
    double t136 = 1.0 / t135;
    double t137 = 0.5 * (t136 + t135) * VVAR;
    double t138 = sin(t133);
    double t139 = 0.5 * (t135 - t136) * VVAR;
    double t140 = t130 + VAR(eMotion_rotate);
    double t141 = cos(t140);
    double t142 = exp(t132);
    double t143 = 1.0 / t142;
    double t144 = 0.5 * (t143 + t142) * VVAR;
    double t145 = sin(t140);
    double t146 = 0.5 * (t142 - t143) * VVAR;
    double t147 = t131 - VAR(eMotion_move);
    double t148 = exp(-t147);
    double t149 = 1.0 / t148;
    double t150 = 0.5 * (t149 + t148) * VVAR;
    double t151 = 0.5 * (t148 - t149) * VVAR;
    double t152 = exp(t147);
    double t153 = 1.0 / t152;
    double t154 = 0.5 * (t153 + t152) * VVAR;
    double t155 = 0.5 * (t152 - t153) * VVAR;
    double t156 = 0.5 * t6;
    double t157 = (1.0 / t156) * FTx;
    double t158 = acos(t157);
    double t159 = -t158;
    double t160 = acosh(t156);
    double t161 = t160 + VAR(eMotion_move);
    double t162 = t158 + VAR(eMotion_rotate);
    double t163 = cos(t162);
    double t164 = exp(-t161);
    double t165 = 1.0 / t164;
    double t166 = 0.5 * (t165 + t164) * VVAR;
    double t167 = sin(t162);
    double t168 = 0.5 * (t164 - t165) * VVAR;
    double t169 = t159 + VAR(eMotion_rotate);
    double t170 = cos(t169);
    double t171 = exp(t161);
    double t172 = 1.0 / t171;
    double t173 = 0.5 * (t172 + t171) * VVAR;
    double t174 = sin(t169);
    double t175 = 0.5 * (t171 - t172) * VVAR;
    double t176 = t160 - VAR(eMotion_move);
    double t177 = exp(-t176);
    double t178 = 1.0 / t177;
    double t179 = 0.5 * (t178 + t177) * VVAR;
    double t180 = 0.5 * (t177 - t178) * VVAR;
    double t181 = exp(t176);
    double t182 = 1.0 / t181;
    double t183 = 0.5 * (t182 + t181) * VVAR;
    double t184 = 0.5 * (t181 - t182) * VVAR;
    double t185 = (1.0 / 0.0) * FTx;
    double t186 = acos(t185);
    double t187 = -t186;
    double t188 = acosh(0.0);
    double t189 = t188 + VAR(eMotion_move);
    double t190 = t186 + VAR(eMotion_rotate);
    double t191 = cos(t190);
    double t192 = exp(-t189);
    double t193 = 1.0 / t192;
    double t194 = 0.5 * (t193 + t192) * VVAR;
    double t195 = sin(t190);
    double t196 = 0.5 * (t192 - t193) * VVAR;
    double t197 = t187 + VAR(eMotion_rotate);
    double t198 = cos(t197);
    double t199 = exp(t189);
    double t200 = 1.0 / t199;
    double t201 = 0.5 * (t200 + t199) * VVAR;
    double t202 = sin(t197);
    double t203 = 0.5 * (t199 - t200) * VVAR;
    double t204 = t188 - VAR(eMotion_move);
    double t205 = exp(-t204);
    double t206 = 1.0 / t205;
    double t207 = 0.5 * (t206 + t205) * VVAR;
    double t208 = 0.5 * (t205 - t206) * VVAR;
    double t209 = exp(t204);
    double t210 = 1.0 / t209;
    double t211 = 0.5 * (t210 + t209) * VVAR;
    double t212 = 0.5 * (t209 - t210) * VVAR;
    if (t3 <= 0.0) {
        if (0.0 >= t4) {
            if (0.0 >= 1.0) {
                if (t185 > 1.0) {
                    if (FTy >= 0.0) {
                        if (0.0 <= t75) {
                            if (0.0 < t204) {
                                FPx = t78 * t211 + FPx;
                                FPy = t80 * t212 + FPy;
                            } else {
                                FPx = t83 * t207 + FPx;
                                FPy = t85 * t208 + FPy;
                            }
                        } else {
                            if (0.0 < t189) {
                                FPx = t78 * t201 + FPx;
                                FPy = t80 * t203 + FPy;
                            } else {
                                FPx = t83 * t194 + FPx;
                                FPy = t85 * t196 + FPy;
                            }
                        }
                    } else {
                        if (0.0 <= t76) {
                            if (0.0 < t204) {
                                FPx = t83 * t211 + FPx;
                                FPy = t85 * t212 + FPy;
                            } else {
                                FPx = t78 * t207 + FPx;
                                FPy = t80 * t208 + FPy;
                            }
                        } else {
                            if (0.0 < t189) {
                                FPx = t83 * t201 + FPx;
                                FPy = t85 * t203 + FPy;
                            } else {
                                FPx = t78 * t194 + FPx;
                                FPy = t80 * t196 + FPy;
                            }
                        }
                    }
                } else {
                    if (-1.0 > t185) {
                        if (FTy >= 0.0) {
                            if (0.0 <= t51) {
                                if (0.0 < t204) {
                                    FPx = t54 * t211 + FPx;
                                    FPy = t56 * t212 + FPy;
                                } else {
                                    FPx = t59 * t207 + FPx;
                                    FPy = t61 * t208 + FPy;
                                }
                            } else {
                                if (0.0 < t189) {
                                    FPx = t54 * t201 + FPx;
                                    FPy = t56 * t203 + FPy;
                                } else {
                                    FPx = t59 * t194 + FPx;
                                    FPy = t61 * t196 + FPy;
                                }
                            }
                        } else {
                            if (0.0 <= t52) {
                                if (0.0 < t204) {
                                    FPx = t59 * t211 + FPx;
                                    FPy = t61 * t212 + FPy;
                                } else {
                                    FPx = t54 * t207 + FPx;
                                    FPy = t56 * t208 + FPy;
                                }
                            } else {
                                if (0.0 < t189) {
                                    FPx = t59 * t201 + FPx;
                                    FPy = t61 * t203 + FPy;
                                } else {
                                    FPx = t54 * t194 + FPx;
                                    FPy = t56 * t196 + FPy;
                                }
                            }
                        }
                    } else {
                        if (FTy >= 0.0) {
                            if (0.0 <= t186) {
                                if (0.0 < t204) {
                                    FPx = t191 * t211 + FPx;
                                    FPy = t195 * t212 + FPy;
                                } else {
                                    FPx = t198 * t207 + FPx;
                                    FPy = t202 * t208 + FPy;
                                }
                            } else {
                                if (0.0 < t189) {
                                    FPx = t191 * t201 + FPx;
                                    FPy = t195 * t203 + FPy;
                                } else {
                                    FPx = t198 * t194 + FPx;
                                    FPy = t202 * t196 + FPy;
                                }
                            }
                        } else {
                            if (0.0 <= t187) {
                                if (0.0 < t204) {
                                    FPx = t198 * t211 + FPx;
                                    FPy = t202 * t212 + FPy;
                                } else {
                                    FPx = t191 * t207 + FPx;
                                    FPy = t195 * t208 + FPy;
                                }
                            } else {
                                if (0.0 < t189) {
                                    FPx = t198 * t201 + FPx;
                                    FPy = t202 * t203 + FPy;
                                } else {
                                    FPx = t191 * t194 + FPx;
                                    FPy = t195 * t196 + FPy;
                                }
                            }
                        }
                    }
                }
            } else {
                if (FTx > 1.0) {
                    if (FTy >= 0.0) {
                        if (0.0 <= t75) {
                            if (0.0 < t30) {
                                FPx = t97;
                                FPy = t98;
                            } else {
                                FPx = t95;
                                FPy = t96;
                            }
                        } else {
                            if (0.0 < t11) {
                                FPx = t93;
                                FPy = t94;
                            } else {
                                FPx = t91;
                                FPy = t92;
                            }
                        }
                    } else {
                        if (0.0 <= t76) {
                            if (0.0 < t30) {
                                FPx = t89;
                                FPy = t90;
                            } else {
                                FPx = t87;
                                FPy = t88;
                            }
                        } else {
                            if (0.0 < t11) {
                                FPx = t84;
                                FPy = t86;
                            } else {
                                FPx = t79;
                                FPy = t81;
                            }
                        }
                    }
                } else {
                    if (-1.0 > FTx) {
                        if (FTy >= 0.0) {
                            if (0.0 <= t51) {
                                if (0.0 < t30) {
                                    FPx = t73;
                                    FPy = t74;
                                } else {
                                    FPx = t71;
                                    FPy = t72;
                                }
                            } else {
                                if (0.0 < t11) {
                                    FPx = t69;
                                    FPy = t70;
                                } else {
                                    FPx = t67;
                                    FPy = t68;
                                }
                            }
                        } else {
                            if (0.0 <= t52) {
                                if (0.0 < t30) {
                                    FPx = t65;
                                    FPy = t66;
                                } else {
                                    FPx = t63;
                                    FPy = t64;
                                }
                            } else {
                                if (0.0 < t11) {
                                    FPx = t60;
                                    FPy = t62;
                                } else {
                                    FPx = t55;
                                    FPy = t57;
                                }
                            }
                        }
                    } else {
                        if (FTy >= 0.0) {
                            if (0.0 <= t8) {
                                if (0.0 < t30) {
                                    FPx = t49;
                                    FPy = t50;
                                } else {
                                    FPx = t47;
                                    FPy = t48;
                                }
                            } else {
                                if (0.0 < t11) {
                                    FPx = t45;
                                    FPy = t46;
                                } else {
                                    FPx = t43;
                                    FPy = t44;
                                }
                            }
                        } else {
                            if (0.0 <= t9) {
                                if (0.0 < t30) {
                                    FPx = t40;
                                    FPy = t42;
                                } else {
                                    FPx = t34;
                                    FPy = t36;
                                }
                            } else {
                                if (0.0 < t11) {
                                    FPx = t26;
                                    FPy = t29;
                                } else {
                                    FPx = t17;
                                    FPy = t20;
                                }
                            }
                        }
                    }
                }
            }
        } else {
            if (t156 >= 1.0) {
                if (t157 > 1.0) {
                    if (FTy >= 0.0) {
                        if (0.0 <= t75) {
                            if (0.0 < t176) {
                                FPx = t78 * t183 + FPx;
                                FPy = t80 * t184 + FPy;
                            } else {
                                FPx = t83 * t179 + FPx;
                                FPy = t85 * t180 + FPy;
                            }
                        } else {
                            if (0.0 < t161) {
                                FPx = t78 * t173 + FPx;
                                FPy = t80 * t175 + FPy;
                            } else {
                                FPx = t83 * t166 + FPx;
                                FPy = t85 * t168 + FPy;
                            }
                        }
                    } else {
                        if (0.0 <= t76) {
                            if (0.0 < t176) {
                                FPx = t83 * t183 + FPx;
                                FPy = t85 * t184 + FPy;
                            } else {
                                FPx = t78 * t179 + FPx;
                                FPy = t80 * t180 + FPy;
                            }
                        } else {
                            if (0.0 < t161) {
                                FPx = t83 * t173 + FPx;
                                FPy = t85 * t175 + FPy;
                            } else {
                                FPx = t78 * t166 + FPx;
                                FPy = t80 * t168 + FPy;
                            }
                        }
                    }
                } else {
                    if (-1.0 > t157) {
                        if (FTy >= 0.0) {
                            if (0.0 <= t51) {
                                if (0.0 < t176) {
                                    FPx = t54 * t183 + FPx;
                                    FPy = t56 * t184 + FPy;
                                } else {
                                    FPx = t59 * t179 + FPx;
                                    FPy = t61 * t180 + FPy;
                                }
                            } else {
                                if (0.0 < t161) {
                                    FPx = t54 * t173 + FPx;
                                    FPy = t56 * t175 + FPy;
                                } else {
                                    FPx = t59 * t166 + FPx;
                                    FPy = t61 * t168 + FPy;
                                }
                            }
                        } else {
                            if (0.0 <= t52) {
                                if (0.0 < t176) {
                                    FPx = t59 * t183 + FPx;
                                    FPy = t61 * t184 + FPy;
                                } else {
                                    FPx = t54 * t179 + FPx;
                                    FPy = t56 * t180 + FPy;
                                }
                            } else {
                                if (0.0 < t161) {
                                    FPx = t59 * t173 + FPx;
                                    FPy = t61 * t175 + FPy;
                                } else {
                                    FPx = t54 * t166 + FPx;
                                    FPy = t56 * t168 + FPy;
                                }
                            }
                        }
                    } else {
                        if (FTy >= 0.0) {
                            if (0.0 <= t158) {
                                if (0.0 < t176) {
                                    FPx = t163 * t183 + FPx;
                                    FPy = t167 * t184 + FPy;
                                } else {
                                    FPx = t170 * t179 + FPx;
                                    FPy = t174 * t180 + FPy;
                                }
                            } else {
                                if (0.0 < t161) {
                                    FPx = t163 * t173 + FPx;
                                    FPy = t167 * t175 + FPy;
                                } else {
                                    FPx = t170 * t166 + FPx;
                                    FPy = t174 * t168 + FPy;
                                }
                            }
                        } else {
                            if (0.0 <= t159) {
                                if (0.0 < t176) {
                                    FPx = t170 * t183 + FPx;
                                    FPy = t174 * t184 + FPy;
                                } else {
                                    FPx = t163 * t179 + FPx;
                                    FPy = t167 * t180 + FPy;
                                }
                            } else {
                                if (0.0 < t161) {
                                    FPx = t170 * t173 + FPx;
                                    FPy = t174 * t175 + FPy;
                                } else {
                                    FPx = t163 * t166 + FPx;
                                    FPy = t167 * t168 + FPy;
                                }
                            }
                        }
                    }
                }
            } else {
                if (FTx > 1.0) {
                    if (FTy >= 0.0) {
                        if (0.0 <= t75) {
                            if (0.0 < t30) {
                                FPx = t97;
                                FPy = t98;
                            } else {
                                FPx = t95;
                                FPy = t96;
                            }
                        } else {
                            if (0.0 < t11) {
                                FPx = t93;
                                FPy = t94;
                            } else {
                                FPx = t91;
                                FPy = t92;
                            }
                        }
                    } else {
                        if (0.0 <= t76) {
                            if (0.0 < t30) {
                                FPx = t89;
                                FPy = t90;
                            } else {
                                FPx = t87;
                                FPy = t88;
                            }
                        } else {
                            if (0.0 < t11) {
                                FPx = t84;
                                FPy = t86;
                            } else {
                                FPx = t79;
                                FPy = t81;
                            }
                        }
                    }
                } else {
                    if (-1.0 > FTx) {
                        if (FTy >= 0.0) {
                            if (0.0 <= t51) {
                                if (0.0 < t30) {
                                    FPx = t73;
                                    FPy = t74;
                                } else {
                                    FPx = t71;
                                    FPy = t72;
                                }
                            } else {
                                if (0.0 < t11) {
                                    FPx = t69;
                                    FPy = t70;
                                } else {
                                    FPx = t67;
                                    FPy = t68;
                                }
                            }
                        } else {
                            if (0.0 <= t52) {
                                if (0.0 < t30) {
                                    FPx = t65;
                                    FPy = t66;
                                } else {
                                    FPx = t63;
                                    FPy = t64;
                                }
                            } else {
                                if (0.0 < t11) {
                                    FPx = t60;
                                    FPy = t62;
                                } else {
                                    FPx = t55;
                                    FPy = t57;
                                }
                            }
                        }
                    } else {
                        if (FTy >= 0.0) {
                            if (0.0 <= t8) {
                                if (0.0 < t30) {
                                    FPx = t49;
                                    FPy = t50;
                                } else {
                                    FPx = t47;
                                    FPy = t48;
                                }
                            } else {
                                if (0.0 < t11) {
                                    FPx = t45;
                                    FPy = t46;
                                } else {
                                    FPx = t43;
                                    FPy = t44;
                                }
                            }
                        } else {
                            if (0.0 <= t9) {
                                if (0.0 < t30) {
                                    FPx = t40;
                                    FPy = t42;
                                } else {
                                    FPx = t34;
                                    FPy = t36;
                                }
                            } else {
                                if (0.0 < t11) {
                                    FPx = t26;
                                    FPy = t29;
                                } else {
                                    FPx = t17;
                                    FPy = t20;
                                }
                            }
                        }
                    }
                }
            }
        }
    } else {
        if (0.0 >= t4) {
            if (t127 >= 1.0) {
                if (t128 > 1.0) {
                    if (FTy >= 0.0) {
                        if (0.0 <= t75) {
                            if (0.0 < t147) {
                                FPx = t78 * t154 + FPx;
                                FPy = t80 * t155 + FPy;
                            } else {
                                FPx = t83 * t150 + FPx;
                                FPy = t85 * t151 + FPy;
                            }
                        } else {
                            if (0.0 < t132) {
                                FPx = t78 * t144 + FPx;
                                FPy = t80 * t146 + FPy;
                            } else {
                                FPx = t83 * t137 + FPx;
                                FPy = t85 * t139 + FPy;
                            }
                        }
                    } else {
                        if (0.0 <= t76) {
                            if (0.0 < t147) {
                                FPx = t83 * t154 + FPx;
                                FPy = t85 * t155 + FPy;
                            } else {
                                FPx = t78 * t150 + FPx;
                                FPy = t80 * t151 + FPy;
                            }
                        } else {
                            if (0.0 < t132) {
                                FPx = t83 * t144 + FPx;
                                FPy = t85 * t146 + FPy;
                            } else {
                                FPx = t78 * t137 + FPx;
                                FPy = t80 * t139 + FPy;
                            }
                        }
                    }
                } else {
                    if (-1.0 > t128) {
                        if (FTy >= 0.0) {
                            if (0.0 <= t51) {
                                if (0.0 < t147) {
                                    FPx = t54 * t154 + FPx;
                                    FPy = t56 * t155 + FPy;
                                } else {
                                    FPx = t59 * t150 + FPx;
                                    FPy = t61 * t151 + FPy;
                                }
                            } else {
                                if (0.0 < t132) {
                                    FPx = t54 * t144 + FPx;
                                    FPy = t56 * t146 + FPy;
                                } else {
                                    FPx = t59 * t137 + FPx;
                                    FPy = t61 * t139 + FPy;
                                }
                            }
                        } else {
                            if (0.0 <= t52) {
                                if (0.0 < t147) {
                                    FPx = t59 * t154 + FPx;
                                    FPy = t61 * t155 + FPy;
                                } else {
                                    FPx = t54 * t150 + FPx;
                                    FPy = t56 * t151 + FPy;
                                }
                            } else {
                                if (0.0 < t132) {
                                    FPx = t59 * t144 + FPx;
                                    FPy = t61 * t146 + FPy;
                                } else {
                                    FPx = t54 * t137 + FPx;
                                    FPy = t56 * t139 + FPy;
                                }
                            }
                        }
                    } else {
                        if (FTy >= 0.0) {
                            if (0.0 <= t129) {
                                if (0.0 < t147) {
                                    FPx = t134 * t154 + FPx;
                                    FPy = t138 * t155 + FPy;
                                } else {
                                    FPx = t141 * t150 + FPx;
                                    FPy = t145 * t151 + FPy;
                                }
                            } else {
                                if (0.0 < t132) {
                                    FPx = t134 * t144 + FPx;
                                    FPy = t138 * t146 + FPy;
                                } else {
                                    FPx = t141 * t137 + FPx;
                                    FPy = t145 * t139 + FPy;
                                }
                            }
                        } else {
                            if (0.0 <= t130) {
                                if (0.0 < t147) {
                                    FPx = t141 * t154 + FPx;
                                    FPy = t145 * t155 + FPy;
                                } else {
                                    FPx = t134 * t150 + FPx;
                                    FPy = t138 * t151 + FPy;
                                }
                            } else {
                                if (0.0 < t132) {
                                    FPx = t141 * t144 + FPx;
                                    FPy = t145 * t146 + FPy;
                                } else {
                                    FPx = t134 * t137 + FPx;
                                    FPy = t138 * t139 + FPy;
                                }
                            }
                        }
                    }
                }
            } else {
                if (FTx > 1.0) {
                    if (FTy >= 0.0) {
                        if (0.0 <= t75) {
                            if (0.0 < t30) {
                                FPx = t97;
                                FPy = t98;
                            } else {
                                FPx = t95;
                                FPy = t96;
                            }
                        } else {
                            if (0.0 < t11) {
                                FPx = t93;
                                FPy = t94;
                            } else {
                                FPx = t91;
                                FPy = t92;
                            }
                        }
                    } else {
                        if (0.0 <= t76) {
                            if (0.0 < t30) {
                                FPx = t89;
                                FPy = t90;
                            } else {
                                FPx = t87;
                                FPy = t88;
                            }
                        } else {
                            if (0.0 < t11) {
                                FPx = t84;
                                FPy = t86;
                            } else {
                                FPx = t79;
                                FPy = t81;
                            }
                        }
                    }
                } else {
                    if (-1.0 > FTx) {
                        if (FTy >= 0.0) {
                            if (0.0 <= t51) {
                                if (0.0 < t30) {
                                    FPx = t73;
                                    FPy = t74;
                                } else {
                                    FPx = t71;
                                    FPy = t72;
                                }
                            } else {
                                if (0.0 < t11) {
                                    FPx = t69;
                                    FPy = t70;
                                } else {
                                    FPx = t67;
                                    FPy = t68;
                                }
                            }
                        } else {
                            if (0.0 <= t52) {
                                if (0.0 < t30) {
                                    FPx = t65;
                                    FPy = t66;
                                } else {
                                    FPx = t63;
                                    FPy = t64;
                                }
                            } else {
                                if (0.0 < t11) {
                                    FPx = t60;
                                    FPy = t62;
                                } else {
                                    FPx = t55;
                                    FPy = t57;
                                }
                            }
                        }
                    } else {
                        if (FTy >= 0.0) {
                            if (0.0 <= t8) {
                                if (0.0 < t30) {
                                    FPx = t49;
                                    FPy = t50;
                                } else {
                                    FPx = t47;
                                    FPy = t48;
                                }
                            } else {
                                if (0.0 < t11) {
                                    FPx = t45;
                                    FPy = t46;
                                } else {
                                    FPx = t43;
                                    FPy = t44;
                                }
                            }
                        } else {
                            if (0.0 <= t9) {
                                if (0.0 < t30) {
                                    FPx = t40;
                                    FPy = t42;
                                } else {
                                    FPx = t34;
                                    FPy = t36;
                                }
                            } else {
                                if (0.0 < t11) {
                                    FPx = t26;
                                    FPy = t29;
                                } else {
                                    FPx = t17;
                                    FPy = t20;
                                }
                            }
                        }
                    }
                }
            }
        } else {
            if (t7 >= 1.0) {
                if (t99 > 1.0) {
                    if (FTy >= 0.0) {
                        if (0.0 <= t75) {
                            if (0.0 < t118) {
                                FPx = t78 * t125 + FPx;
                                FPy = t80 * t126 + FPy;
                            } else {
                                FPx = t83 * t121 + FPx;
                                FPy = t85 * t122 + FPy;
                            }
                        } else {
                            if (0.0 < t103) {
                                FPx = t78 * t115 + FPx;
                                FPy = t80 * t117 + FPy;
                            } else {
                                FPx = t83 * t108 + FPx;
                                FPy = t85 * t110 + FPy;
                            }
                        }
                    } else {
                        if (0.0 <= t76) {
                            if (0.0 < t118) {
                                FPx = t83 * t125 + FPx;
                                FPy = t85 * t126 + FPy;
                            } else {
                                FPx = t78 * t121 + FPx;
                                FPy = t80 * t122 + FPy;
                            }
                        } else {
                            if (0.0 < t103) {
                                FPx = t83 * t115 + FPx;
                                FPy = t85 * t117 + FPy;
                            } else {
                                FPx = t78 * t108 + FPx;
                                FPy = t80 * t110 + FPy;
                            }
                        }
                    }
                } else {
                    if (-1.0 > t99) {
                        if (FTy >= 0.0) {
                            if (0.0 <= t51) {
                                if (0.0 < t118) {
                                    FPx = t54 * t125 + FPx;
                                    FPy = t56 * t126 + FPy;
                                } else {
                                    FPx = t59 * t121 + FPx;
                                    FPy = t61 * t122 + FPy;
                                }
                            } else {
                                if (0.0 < t103) {
                                    FPx = t54 * t115 + FPx;
                                    FPy = t56 * t117 + FPy;
                                } else {
                                    FPx = t59 * t108 + FPx;
                                    FPy = t61 * t110 + FPy;
                                }
                            }
                        } else {
                            if (0.0 <= t52) {
                                if (0.0 < t118) {
                                    FPx = t59 * t125 + FPx;
                                    FPy = t61 * t126 + FPy;
                                } else {
                                    FPx = t54 * t121 + FPx;
                                    FPy = t56 * t122 + FPy;
                                }
                            } else {
                                if (0.0 < t103) {
                                    FPx = t59 * t115 + FPx;
                                    FPy = t61 * t117 + FPy;
                                } else {
                                    FPx = t54 * t108 + FPx;
                                    FPy = t56 * t110 + FPy;
                                }
                            }
                        }
                    } else {
                        if (FTy >= 0.0) {
                            if (0.0 <= t100) {
                                if (0.0 < t118) {
                                    FPx = t105 * t125 + FPx;
                                    FPy = t109 * t126 + FPy;
                                } else {
                                    FPx = t112 * t121 + FPx;
                                    FPy = t116 * t122 + FPy;
                                }
                            } else {
                                if (0.0 < t103) {
                                    FPx = t105 * t115 + FPx;
                                    FPy = t109 * t117 + FPy;
                                } else {
                                    FPx = t112 * t108 + FPx;
                                    FPy = t116 * t110 + FPy;
                                }
                            }
                        } else {
                            if (0.0 <= t101) {
                                if (0.0 < t118) {
                                    FPx = t112 * t125 + FPx;
                                    FPy = t116 * t126 + FPy;
                                } else {
                                    FPx = t105 * t121 + FPx;
                                    FPy = t109 * t122 + FPy;
                                }
                            } else {
                                if (0.0 < t103) {
                                    FPx = t112 * t115 + FPx;
                                    FPy = t116 * t117 + FPy;
                                } else {
                                    FPx = t105 * t108 + FPx;
                                    FPy = t109 * t110 + FPy;
                                }
                            }
                        }
                    }
                }
            } else {
                if (FTx > 1.0) {
                    if (FTy >= 0.0) {
                        if (0.0 <= t75) {
                            if (0.0 < t30) {
                                FPx = t97;
                                FPy = t98;
                            } else {
                                FPx = t95;
                                FPy = t96;
                            }
                        } else {
                            if (0.0 < t11) {
                                FPx = t93;
                                FPy = t94;
                            } else {
                                FPx = t91;
                                FPy = t92;
                            }
                        }
                    } else {
                        if (0.0 <= t76) {
                            if (0.0 < t30) {
                                FPx = t89;
                                FPy = t90;
                            } else {
                                FPx = t87;
                                FPy = t88;
                            }
                        } else {
                            if (0.0 < t11) {
                                FPx = t84;
                                FPy = t86;
                            } else {
                                FPx = t79;
                                FPy = t81;
                            }
                        }
                    }
                } else {
                    if (-1.0 > FTx) {
                        if (FTy >= 0.0) {
                            if (0.0 <= t51) {
                                if (0.0 < t30) {
                                    FPx = t73;
                                    FPy = t74;
                                } else {
                                    FPx = t71;
                                    FPy = t72;
                                }
                            } else {
                                if (0.0 < t11) {
                                    FPx = t69;
                                    FPy = t70;
                                } else {
                                    FPx = t67;
                                    FPy = t68;
                                }
                            }
                        } else {
                            if (0.0 <= t52) {
                                if (0.0 < t30) {
                                    FPx = t65;
                                    FPy = t66;
                                } else {
                                    FPx = t63;
                                    FPy = t64;
                                }
                            } else {
                                if (0.0 < t11) {
                                    FPx = t60;
                                    FPy = t62;
                                } else {
                                    FPx = t55;
                                    FPy = t57;
                                }
                            }
                        }
                    } else {
                        if (FTy >= 0.0) {
                            if (0.0 <= t8) {
                                if (0.0 < t30) {
                                    FPx = t49;
                                    FPy = t50;
                                } else {
                                    FPx = t47;
                                    FPy = t48;
                                }
                            } else {
                                if (0.0 < t11) {
                                    FPx = t45;
                                    FPy = t46;
                                } else {
                                    FPx = t43;
                                    FPy = t44;
                                }
                            }
                        } else {
                            if (0.0 <= t9) {
                                if (0.0 < t30) {
                                    FPx = t40;
                                    FPy = t42;
                                } else {
                                    FPx = t34;
                                    FPy = t36;
                                }
                            } else {
                                if (0.0 < t11) {
                                    FPx = t26;
                                    FPy = t29;
                                } else {
                                    FPx = t17;
                                    FPy = t20;
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