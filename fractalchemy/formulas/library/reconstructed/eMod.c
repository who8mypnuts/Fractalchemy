/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        eMod.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from eMod.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double eMod_radius;
    double eMod_distance;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("eMod");
APO_VARIABLES(
    VAR_REAL(eMod_radius, 1.0),
    VAR_REAL_CYCLE(eMod_distance, 0.0, 2.0, 0.0)
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
    double t8 = acosh(1.0);
    double t9 = acos(FTx);
    double t10 = cos(t9);
    double t11 = exp(t8);
    double t12 = 1.0 / t11;
    double t13 = 0.5 * (t12 + t11) * VVAR;
    double t14 = t10 * t13 + FPx;
    double t15 = sin(t9);
    double t16 = 0.5 * (t11 - t12) * VVAR;
    double t17 = t15 * t16 + FPy;
    double t18 = VAR(eMod_distance) * VAR(eMod_radius);
    double t19 = VAR(eMod_radius) + VAR(eMod_radius);
    double t20 = exp(fmod(t18 + (t8 + VAR(eMod_radius)), t19) - VAR(eMod_radius));
    double t21 = 1.0 / t20;
    double t22 = 0.5 * (t21 + t20) * VVAR;
    double t23 = t10 * t22 + FPx;
    double t24 = 0.5 * (t20 - t21) * VVAR;
    double t25 = t15 * t24 + FPy;
    double t26 = exp(fmod((t8 - VAR(eMod_radius)) - t18, t19) + VAR(eMod_radius));
    double t27 = 1.0 / t26;
    double t28 = 0.5 * (t27 + t26) * VVAR;
    double t29 = t10 * t28 + FPx;
    double t30 = 0.5 * (t26 - t27) * VVAR;
    double t31 = t15 * t30 + FPy;
    double t32 = acos(-1.0);
    double t33 = cos(t32);
    double t34 = t33 * t13 + FPx;
    double t35 = sin(t32);
    double t36 = t35 * t16 + FPy;
    double t37 = t33 * t22 + FPx;
    double t38 = t35 * t24 + FPy;
    double t39 = t33 * t28 + FPx;
    double t40 = t35 * t30 + FPy;
    double t41 = acos(1.0);
    double t42 = cos(t41);
    double t43 = t42 * t13 + FPx;
    double t44 = sin(t41);
    double t45 = t44 * t16 + FPy;
    double t46 = t42 * t22 + FPx;
    double t47 = t44 * t24 + FPy;
    double t48 = t42 * t28 + FPx;
    double t49 = t44 * t30 + FPy;
    double t50 = (1.0 / t7) * FTx;
    double t51 = acosh(t7);
    double t52 = acos(t50);
    double t53 = cos(t52);
    double t54 = exp(t51);
    double t55 = 1.0 / t54;
    double t56 = 0.5 * (t55 + t54) * VVAR;
    double t57 = t53 * t56 + FPx;
    double t58 = sin(t52);
    double t59 = 0.5 * (t54 - t55) * VVAR;
    double t60 = t58 * t59 + FPy;
    double t61 = exp(fmod(t18 + (t51 + VAR(eMod_radius)), t19) - VAR(eMod_radius));
    double t62 = 1.0 / t61;
    double t63 = 0.5 * (t62 + t61) * VVAR;
    double t64 = t53 * t63 + FPx;
    double t65 = 0.5 * (t61 - t62) * VVAR;
    double t66 = t58 * t65 + FPy;
    double t67 = exp(fmod((t51 - VAR(eMod_radius)) - t18, t19) + VAR(eMod_radius));
    double t68 = 1.0 / t67;
    double t69 = 0.5 * (t68 + t67) * VVAR;
    double t70 = t53 * t69 + FPx;
    double t71 = 0.5 * (t67 - t68) * VVAR;
    double t72 = t58 * t71 + FPy;
    double t73 = t33 * t56 + FPx;
    double t74 = t35 * t59 + FPy;
    double t75 = t33 * t63 + FPx;
    double t76 = t35 * t65 + FPy;
    double t77 = t33 * t69 + FPx;
    double t78 = t35 * t71 + FPy;
    double t79 = t42 * t56 + FPx;
    double t80 = t44 * t59 + FPy;
    double t81 = t42 * t63 + FPx;
    double t82 = t44 * t65 + FPy;
    double t83 = t42 * t69 + FPx;
    double t84 = t44 * t71 + FPy;
    double t85 = 0.5 * t5;
    double t86 = (1.0 / t85) * FTx;
    double t87 = acosh(t85);
    double t88 = acos(t86);
    double t89 = cos(t88);
    double t90 = exp(t87);
    double t91 = 1.0 / t90;
    double t92 = 0.5 * (t91 + t90) * VVAR;
    double t93 = t89 * t92 + FPx;
    double t94 = sin(t88);
    double t95 = 0.5 * (t90 - t91) * VVAR;
    double t96 = t94 * t95 + FPy;
    double t97 = exp(fmod(t18 + (t87 + VAR(eMod_radius)), t19) - VAR(eMod_radius));
    double t98 = 1.0 / t97;
    double t99 = 0.5 * (t98 + t97) * VVAR;
    double t100 = t89 * t99 + FPx;
    double t101 = 0.5 * (t97 - t98) * VVAR;
    double t102 = t94 * t101 + FPy;
    double t103 = exp(fmod((t87 - VAR(eMod_radius)) - t18, t19) + VAR(eMod_radius));
    double t104 = 1.0 / t103;
    double t105 = 0.5 * (t104 + t103) * VVAR;
    double t106 = t89 * t105 + FPx;
    double t107 = 0.5 * (t103 - t104) * VVAR;
    double t108 = t94 * t107 + FPy;
    double t109 = t33 * t92 + FPx;
    double t110 = t35 * t95 + FPy;
    double t111 = t33 * t99 + FPx;
    double t112 = t35 * t101 + FPy;
    double t113 = t33 * t105 + FPx;
    double t114 = t35 * t107 + FPy;
    double t115 = t42 * t92 + FPx;
    double t116 = t44 * t95 + FPy;
    double t117 = t42 * t99 + FPx;
    double t118 = t44 * t101 + FPy;
    double t119 = t42 * t105 + FPx;
    double t120 = t44 * t107 + FPy;
    double t121 = 0.5 * t6;
    double t122 = (1.0 / t121) * FTx;
    double t123 = acosh(t121);
    double t124 = acos(t122);
    double t125 = cos(t124);
    double t126 = exp(t123);
    double t127 = 1.0 / t126;
    double t128 = 0.5 * (t127 + t126) * VVAR;
    double t129 = t125 * t128 + FPx;
    double t130 = sin(t124);
    double t131 = 0.5 * (t126 - t127) * VVAR;
    double t132 = t130 * t131 + FPy;
    double t133 = exp(fmod(t18 + (t123 + VAR(eMod_radius)), t19) - VAR(eMod_radius));
    double t134 = 1.0 / t133;
    double t135 = 0.5 * (t134 + t133) * VVAR;
    double t136 = t125 * t135 + FPx;
    double t137 = 0.5 * (t133 - t134) * VVAR;
    double t138 = t130 * t137 + FPy;
    double t139 = exp(fmod((t123 - VAR(eMod_radius)) - t18, t19) + VAR(eMod_radius));
    double t140 = 1.0 / t139;
    double t141 = 0.5 * (t140 + t139) * VVAR;
    double t142 = t125 * t141 + FPx;
    double t143 = 0.5 * (t139 - t140) * VVAR;
    double t144 = t130 * t143 + FPy;
    double t145 = t33 * t128 + FPx;
    double t146 = t35 * t131 + FPy;
    double t147 = t33 * t135 + FPx;
    double t148 = t35 * t137 + FPy;
    double t149 = t33 * t141 + FPx;
    double t150 = t35 * t143 + FPy;
    double t151 = t42 * t128 + FPx;
    double t152 = t44 * t131 + FPy;
    double t153 = t42 * t135 + FPx;
    double t154 = t44 * t137 + FPy;
    double t155 = t42 * t141 + FPx;
    double t156 = t44 * t143 + FPy;
    double t157 = (1.0 / 0.0) * FTx;
    double t158 = acosh(0.0);
    double t159 = acos(t157);
    double t160 = cos(t159);
    double t161 = exp(t158);
    double t162 = 1.0 / t161;
    double t163 = 0.5 * (t162 + t161) * VVAR;
    double t164 = t160 * t163 + FPx;
    double t165 = sin(t159);
    double t166 = 0.5 * (t161 - t162) * VVAR;
    double t167 = t165 * t166 + FPy;
    double t168 = exp(fmod(t18 + (t158 + VAR(eMod_radius)), t19) - VAR(eMod_radius));
    double t169 = 1.0 / t168;
    double t170 = 0.5 * (t169 + t168) * VVAR;
    double t171 = t160 * t170 + FPx;
    double t172 = 0.5 * (t168 - t169) * VVAR;
    double t173 = t165 * t172 + FPy;
    double t174 = exp(fmod((t158 - VAR(eMod_radius)) - t18, t19) + VAR(eMod_radius));
    double t175 = 1.0 / t174;
    double t176 = 0.5 * (t175 + t174) * VVAR;
    double t177 = t160 * t176 + FPx;
    double t178 = 0.5 * (t174 - t175) * VVAR;
    double t179 = t165 * t178 + FPy;
    double t180 = t33 * t163 + FPx;
    double t181 = t35 * t166 + FPy;
    double t182 = t33 * t170 + FPx;
    double t183 = t35 * t172 + FPy;
    double t184 = t33 * t176 + FPx;
    double t185 = t35 * t178 + FPy;
    double t186 = t42 * t163 + FPx;
    double t187 = t44 * t166 + FPy;
    double t188 = t42 * t170 + FPx;
    double t189 = t44 * t172 + FPy;
    double t190 = t42 * t176 + FPx;
    double t191 = t44 * t178 + FPy;
    if (t3 <= 0.0) {
        if (0.0 >= t4) {
            if (0.0 >= 1.0) {
                if (t157 > 1.0) {
                    if (FTy >= 0.0) {
                        if (VAR(eMod_radius) <= t158) {
                            FPx = t186;
                            FPy = t187;
                        } else {
                            if (-t158 < VAR(eMod_radius)) {
                                if (0.0 >= t41) {
                                    FPx = t190;
                                    FPy = t191;
                                } else {
                                    FPx = t188;
                                    FPy = t189;
                                }
                            } else {
                                FPx = t186;
                                FPy = t187;
                            }
                        }
                    } else {
                        if (VAR(eMod_radius) <= t158) {
                            FPx = t186;
                            FPy = t187;
                        } else {
                            if (-t158 < VAR(eMod_radius)) {
                                if (0.0 >= t41) {
                                    FPx = t190;
                                    FPy = t191;
                                } else {
                                    FPx = t188;
                                    FPy = t189;
                                }
                            } else {
                                FPx = t186;
                                FPy = t187;
                            }
                        }
                    }
                } else {
                    if (-1.0 > t157) {
                        if (FTy >= 0.0) {
                            if (VAR(eMod_radius) <= t158) {
                                FPx = t180;
                                FPy = t181;
                            } else {
                                if (-t158 < VAR(eMod_radius)) {
                                    if (0.0 >= t32) {
                                        FPx = t184;
                                        FPy = t185;
                                    } else {
                                        FPx = t182;
                                        FPy = t183;
                                    }
                                } else {
                                    FPx = t180;
                                    FPy = t181;
                                }
                            }
                        } else {
                            if (VAR(eMod_radius) <= t158) {
                                FPx = t180;
                                FPy = t181;
                            } else {
                                if (-t158 < VAR(eMod_radius)) {
                                    if (0.0 >= t32) {
                                        FPx = t184;
                                        FPy = t185;
                                    } else {
                                        FPx = t182;
                                        FPy = t183;
                                    }
                                } else {
                                    FPx = t180;
                                    FPy = t181;
                                }
                            }
                        }
                    } else {
                        if (FTy >= 0.0) {
                            if (VAR(eMod_radius) <= t158) {
                                FPx = t164;
                                FPy = t167;
                            } else {
                                if (-t158 < VAR(eMod_radius)) {
                                    if (0.0 >= t159) {
                                        FPx = t177;
                                        FPy = t179;
                                    } else {
                                        FPx = t171;
                                        FPy = t173;
                                    }
                                } else {
                                    FPx = t164;
                                    FPy = t167;
                                }
                            }
                        } else {
                            if (VAR(eMod_radius) <= t158) {
                                FPx = t164;
                                FPy = t167;
                            } else {
                                if (-t158 < VAR(eMod_radius)) {
                                    if (0.0 >= t159) {
                                        FPx = t177;
                                        FPy = t179;
                                    } else {
                                        FPx = t171;
                                        FPy = t173;
                                    }
                                } else {
                                    FPx = t164;
                                    FPy = t167;
                                }
                            }
                        }
                    }
                }
            } else {
                if (FTx > 1.0) {
                    if (FTy >= 0.0) {
                        if (VAR(eMod_radius) <= t8) {
                            FPx = t43;
                            FPy = t45;
                        } else {
                            if (-t8 < VAR(eMod_radius)) {
                                if (0.0 >= t41) {
                                    FPx = t48;
                                    FPy = t49;
                                } else {
                                    FPx = t46;
                                    FPy = t47;
                                }
                            } else {
                                FPx = t43;
                                FPy = t45;
                            }
                        }
                    } else {
                        if (VAR(eMod_radius) <= t8) {
                            FPx = t43;
                            FPy = t45;
                        } else {
                            if (-t8 < VAR(eMod_radius)) {
                                if (0.0 >= t41) {
                                    FPx = t48;
                                    FPy = t49;
                                } else {
                                    FPx = t46;
                                    FPy = t47;
                                }
                            } else {
                                FPx = t43;
                                FPy = t45;
                            }
                        }
                    }
                } else {
                    if (-1.0 > FTx) {
                        if (FTy >= 0.0) {
                            if (VAR(eMod_radius) <= t8) {
                                FPx = t34;
                                FPy = t36;
                            } else {
                                if (-t8 < VAR(eMod_radius)) {
                                    if (0.0 >= t32) {
                                        FPx = t39;
                                        FPy = t40;
                                    } else {
                                        FPx = t37;
                                        FPy = t38;
                                    }
                                } else {
                                    FPx = t34;
                                    FPy = t36;
                                }
                            }
                        } else {
                            if (VAR(eMod_radius) <= t8) {
                                FPx = t34;
                                FPy = t36;
                            } else {
                                if (-t8 < VAR(eMod_radius)) {
                                    if (0.0 >= t32) {
                                        FPx = t39;
                                        FPy = t40;
                                    } else {
                                        FPx = t37;
                                        FPy = t38;
                                    }
                                } else {
                                    FPx = t34;
                                    FPy = t36;
                                }
                            }
                        }
                    } else {
                        if (FTy >= 0.0) {
                            if (VAR(eMod_radius) <= t8) {
                                FPx = t14;
                                FPy = t17;
                            } else {
                                if (-t8 < VAR(eMod_radius)) {
                                    if (0.0 >= t9) {
                                        FPx = t29;
                                        FPy = t31;
                                    } else {
                                        FPx = t23;
                                        FPy = t25;
                                    }
                                } else {
                                    FPx = t14;
                                    FPy = t17;
                                }
                            }
                        } else {
                            if (VAR(eMod_radius) <= t8) {
                                FPx = t14;
                                FPy = t17;
                            } else {
                                if (-t8 < VAR(eMod_radius)) {
                                    if (0.0 >= t9) {
                                        FPx = t29;
                                        FPy = t31;
                                    } else {
                                        FPx = t23;
                                        FPy = t25;
                                    }
                                } else {
                                    FPx = t14;
                                    FPy = t17;
                                }
                            }
                        }
                    }
                }
            }
        } else {
            if (t121 >= 1.0) {
                if (t122 > 1.0) {
                    if (FTy >= 0.0) {
                        if (VAR(eMod_radius) <= t123) {
                            FPx = t151;
                            FPy = t152;
                        } else {
                            if (-t123 < VAR(eMod_radius)) {
                                if (0.0 >= t41) {
                                    FPx = t155;
                                    FPy = t156;
                                } else {
                                    FPx = t153;
                                    FPy = t154;
                                }
                            } else {
                                FPx = t151;
                                FPy = t152;
                            }
                        }
                    } else {
                        if (VAR(eMod_radius) <= t123) {
                            FPx = t151;
                            FPy = t152;
                        } else {
                            if (-t123 < VAR(eMod_radius)) {
                                if (0.0 >= t41) {
                                    FPx = t155;
                                    FPy = t156;
                                } else {
                                    FPx = t153;
                                    FPy = t154;
                                }
                            } else {
                                FPx = t151;
                                FPy = t152;
                            }
                        }
                    }
                } else {
                    if (-1.0 > t122) {
                        if (FTy >= 0.0) {
                            if (VAR(eMod_radius) <= t123) {
                                FPx = t145;
                                FPy = t146;
                            } else {
                                if (-t123 < VAR(eMod_radius)) {
                                    if (0.0 >= t32) {
                                        FPx = t149;
                                        FPy = t150;
                                    } else {
                                        FPx = t147;
                                        FPy = t148;
                                    }
                                } else {
                                    FPx = t145;
                                    FPy = t146;
                                }
                            }
                        } else {
                            if (VAR(eMod_radius) <= t123) {
                                FPx = t145;
                                FPy = t146;
                            } else {
                                if (-t123 < VAR(eMod_radius)) {
                                    if (0.0 >= t32) {
                                        FPx = t149;
                                        FPy = t150;
                                    } else {
                                        FPx = t147;
                                        FPy = t148;
                                    }
                                } else {
                                    FPx = t145;
                                    FPy = t146;
                                }
                            }
                        }
                    } else {
                        if (FTy >= 0.0) {
                            if (VAR(eMod_radius) <= t123) {
                                FPx = t129;
                                FPy = t132;
                            } else {
                                if (-t123 < VAR(eMod_radius)) {
                                    if (0.0 >= t124) {
                                        FPx = t142;
                                        FPy = t144;
                                    } else {
                                        FPx = t136;
                                        FPy = t138;
                                    }
                                } else {
                                    FPx = t129;
                                    FPy = t132;
                                }
                            }
                        } else {
                            if (VAR(eMod_radius) <= t123) {
                                FPx = t129;
                                FPy = t132;
                            } else {
                                if (-t123 < VAR(eMod_radius)) {
                                    if (0.0 >= t124) {
                                        FPx = t142;
                                        FPy = t144;
                                    } else {
                                        FPx = t136;
                                        FPy = t138;
                                    }
                                } else {
                                    FPx = t129;
                                    FPy = t132;
                                }
                            }
                        }
                    }
                }
            } else {
                if (FTx > 1.0) {
                    if (FTy >= 0.0) {
                        if (VAR(eMod_radius) <= t8) {
                            FPx = t43;
                            FPy = t45;
                        } else {
                            if (-t8 < VAR(eMod_radius)) {
                                if (0.0 >= t41) {
                                    FPx = t48;
                                    FPy = t49;
                                } else {
                                    FPx = t46;
                                    FPy = t47;
                                }
                            } else {
                                FPx = t43;
                                FPy = t45;
                            }
                        }
                    } else {
                        if (VAR(eMod_radius) <= t8) {
                            FPx = t43;
                            FPy = t45;
                        } else {
                            if (-t8 < VAR(eMod_radius)) {
                                if (0.0 >= t41) {
                                    FPx = t48;
                                    FPy = t49;
                                } else {
                                    FPx = t46;
                                    FPy = t47;
                                }
                            } else {
                                FPx = t43;
                                FPy = t45;
                            }
                        }
                    }
                } else {
                    if (-1.0 > FTx) {
                        if (FTy >= 0.0) {
                            if (VAR(eMod_radius) <= t8) {
                                FPx = t34;
                                FPy = t36;
                            } else {
                                if (-t8 < VAR(eMod_radius)) {
                                    if (0.0 >= t32) {
                                        FPx = t39;
                                        FPy = t40;
                                    } else {
                                        FPx = t37;
                                        FPy = t38;
                                    }
                                } else {
                                    FPx = t34;
                                    FPy = t36;
                                }
                            }
                        } else {
                            if (VAR(eMod_radius) <= t8) {
                                FPx = t34;
                                FPy = t36;
                            } else {
                                if (-t8 < VAR(eMod_radius)) {
                                    if (0.0 >= t32) {
                                        FPx = t39;
                                        FPy = t40;
                                    } else {
                                        FPx = t37;
                                        FPy = t38;
                                    }
                                } else {
                                    FPx = t34;
                                    FPy = t36;
                                }
                            }
                        }
                    } else {
                        if (FTy >= 0.0) {
                            if (VAR(eMod_radius) <= t8) {
                                FPx = t14;
                                FPy = t17;
                            } else {
                                if (-t8 < VAR(eMod_radius)) {
                                    if (0.0 >= t9) {
                                        FPx = t29;
                                        FPy = t31;
                                    } else {
                                        FPx = t23;
                                        FPy = t25;
                                    }
                                } else {
                                    FPx = t14;
                                    FPy = t17;
                                }
                            }
                        } else {
                            if (VAR(eMod_radius) <= t8) {
                                FPx = t14;
                                FPy = t17;
                            } else {
                                if (-t8 < VAR(eMod_radius)) {
                                    if (0.0 >= t9) {
                                        FPx = t29;
                                        FPy = t31;
                                    } else {
                                        FPx = t23;
                                        FPy = t25;
                                    }
                                } else {
                                    FPx = t14;
                                    FPy = t17;
                                }
                            }
                        }
                    }
                }
            }
        }
    } else {
        if (0.0 >= t4) {
            if (t85 >= 1.0) {
                if (t86 > 1.0) {
                    if (FTy >= 0.0) {
                        if (VAR(eMod_radius) <= t87) {
                            FPx = t115;
                            FPy = t116;
                        } else {
                            if (-t87 < VAR(eMod_radius)) {
                                if (0.0 >= t41) {
                                    FPx = t119;
                                    FPy = t120;
                                } else {
                                    FPx = t117;
                                    FPy = t118;
                                }
                            } else {
                                FPx = t115;
                                FPy = t116;
                            }
                        }
                    } else {
                        if (VAR(eMod_radius) <= t87) {
                            FPx = t115;
                            FPy = t116;
                        } else {
                            if (-t87 < VAR(eMod_radius)) {
                                if (0.0 >= t41) {
                                    FPx = t119;
                                    FPy = t120;
                                } else {
                                    FPx = t117;
                                    FPy = t118;
                                }
                            } else {
                                FPx = t115;
                                FPy = t116;
                            }
                        }
                    }
                } else {
                    if (-1.0 > t86) {
                        if (FTy >= 0.0) {
                            if (VAR(eMod_radius) <= t87) {
                                FPx = t109;
                                FPy = t110;
                            } else {
                                if (-t87 < VAR(eMod_radius)) {
                                    if (0.0 >= t32) {
                                        FPx = t113;
                                        FPy = t114;
                                    } else {
                                        FPx = t111;
                                        FPy = t112;
                                    }
                                } else {
                                    FPx = t109;
                                    FPy = t110;
                                }
                            }
                        } else {
                            if (VAR(eMod_radius) <= t87) {
                                FPx = t109;
                                FPy = t110;
                            } else {
                                if (-t87 < VAR(eMod_radius)) {
                                    if (0.0 >= t32) {
                                        FPx = t113;
                                        FPy = t114;
                                    } else {
                                        FPx = t111;
                                        FPy = t112;
                                    }
                                } else {
                                    FPx = t109;
                                    FPy = t110;
                                }
                            }
                        }
                    } else {
                        if (FTy >= 0.0) {
                            if (VAR(eMod_radius) <= t87) {
                                FPx = t93;
                                FPy = t96;
                            } else {
                                if (-t87 < VAR(eMod_radius)) {
                                    if (0.0 >= t88) {
                                        FPx = t106;
                                        FPy = t108;
                                    } else {
                                        FPx = t100;
                                        FPy = t102;
                                    }
                                } else {
                                    FPx = t93;
                                    FPy = t96;
                                }
                            }
                        } else {
                            if (VAR(eMod_radius) <= t87) {
                                FPx = t93;
                                FPy = t96;
                            } else {
                                if (-t87 < VAR(eMod_radius)) {
                                    if (0.0 >= t88) {
                                        FPx = t106;
                                        FPy = t108;
                                    } else {
                                        FPx = t100;
                                        FPy = t102;
                                    }
                                } else {
                                    FPx = t93;
                                    FPy = t96;
                                }
                            }
                        }
                    }
                }
            } else {
                if (FTx > 1.0) {
                    if (FTy >= 0.0) {
                        if (VAR(eMod_radius) <= t8) {
                            FPx = t43;
                            FPy = t45;
                        } else {
                            if (-t8 < VAR(eMod_radius)) {
                                if (0.0 >= t41) {
                                    FPx = t48;
                                    FPy = t49;
                                } else {
                                    FPx = t46;
                                    FPy = t47;
                                }
                            } else {
                                FPx = t43;
                                FPy = t45;
                            }
                        }
                    } else {
                        if (VAR(eMod_radius) <= t8) {
                            FPx = t43;
                            FPy = t45;
                        } else {
                            if (-t8 < VAR(eMod_radius)) {
                                if (0.0 >= t41) {
                                    FPx = t48;
                                    FPy = t49;
                                } else {
                                    FPx = t46;
                                    FPy = t47;
                                }
                            } else {
                                FPx = t43;
                                FPy = t45;
                            }
                        }
                    }
                } else {
                    if (-1.0 > FTx) {
                        if (FTy >= 0.0) {
                            if (VAR(eMod_radius) <= t8) {
                                FPx = t34;
                                FPy = t36;
                            } else {
                                if (-t8 < VAR(eMod_radius)) {
                                    if (0.0 >= t32) {
                                        FPx = t39;
                                        FPy = t40;
                                    } else {
                                        FPx = t37;
                                        FPy = t38;
                                    }
                                } else {
                                    FPx = t34;
                                    FPy = t36;
                                }
                            }
                        } else {
                            if (VAR(eMod_radius) <= t8) {
                                FPx = t34;
                                FPy = t36;
                            } else {
                                if (-t8 < VAR(eMod_radius)) {
                                    if (0.0 >= t32) {
                                        FPx = t39;
                                        FPy = t40;
                                    } else {
                                        FPx = t37;
                                        FPy = t38;
                                    }
                                } else {
                                    FPx = t34;
                                    FPy = t36;
                                }
                            }
                        }
                    } else {
                        if (FTy >= 0.0) {
                            if (VAR(eMod_radius) <= t8) {
                                FPx = t14;
                                FPy = t17;
                            } else {
                                if (-t8 < VAR(eMod_radius)) {
                                    if (0.0 >= t9) {
                                        FPx = t29;
                                        FPy = t31;
                                    } else {
                                        FPx = t23;
                                        FPy = t25;
                                    }
                                } else {
                                    FPx = t14;
                                    FPy = t17;
                                }
                            }
                        } else {
                            if (VAR(eMod_radius) <= t8) {
                                FPx = t14;
                                FPy = t17;
                            } else {
                                if (-t8 < VAR(eMod_radius)) {
                                    if (0.0 >= t9) {
                                        FPx = t29;
                                        FPy = t31;
                                    } else {
                                        FPx = t23;
                                        FPy = t25;
                                    }
                                } else {
                                    FPx = t14;
                                    FPy = t17;
                                }
                            }
                        }
                    }
                }
            }
        } else {
            if (t7 >= 1.0) {
                if (t50 > 1.0) {
                    if (FTy >= 0.0) {
                        if (VAR(eMod_radius) <= t51) {
                            FPx = t79;
                            FPy = t80;
                        } else {
                            if (-t51 < VAR(eMod_radius)) {
                                if (0.0 >= t41) {
                                    FPx = t83;
                                    FPy = t84;
                                } else {
                                    FPx = t81;
                                    FPy = t82;
                                }
                            } else {
                                FPx = t79;
                                FPy = t80;
                            }
                        }
                    } else {
                        if (VAR(eMod_radius) <= t51) {
                            FPx = t79;
                            FPy = t80;
                        } else {
                            if (-t51 < VAR(eMod_radius)) {
                                if (0.0 >= t41) {
                                    FPx = t83;
                                    FPy = t84;
                                } else {
                                    FPx = t81;
                                    FPy = t82;
                                }
                            } else {
                                FPx = t79;
                                FPy = t80;
                            }
                        }
                    }
                } else {
                    if (-1.0 > t50) {
                        if (FTy >= 0.0) {
                            if (VAR(eMod_radius) <= t51) {
                                FPx = t73;
                                FPy = t74;
                            } else {
                                if (-t51 < VAR(eMod_radius)) {
                                    if (0.0 >= t32) {
                                        FPx = t77;
                                        FPy = t78;
                                    } else {
                                        FPx = t75;
                                        FPy = t76;
                                    }
                                } else {
                                    FPx = t73;
                                    FPy = t74;
                                }
                            }
                        } else {
                            if (VAR(eMod_radius) <= t51) {
                                FPx = t73;
                                FPy = t74;
                            } else {
                                if (-t51 < VAR(eMod_radius)) {
                                    if (0.0 >= t32) {
                                        FPx = t77;
                                        FPy = t78;
                                    } else {
                                        FPx = t75;
                                        FPy = t76;
                                    }
                                } else {
                                    FPx = t73;
                                    FPy = t74;
                                }
                            }
                        }
                    } else {
                        if (FTy >= 0.0) {
                            if (VAR(eMod_radius) <= t51) {
                                FPx = t57;
                                FPy = t60;
                            } else {
                                if (-t51 < VAR(eMod_radius)) {
                                    if (0.0 >= t52) {
                                        FPx = t70;
                                        FPy = t72;
                                    } else {
                                        FPx = t64;
                                        FPy = t66;
                                    }
                                } else {
                                    FPx = t57;
                                    FPy = t60;
                                }
                            }
                        } else {
                            if (VAR(eMod_radius) <= t51) {
                                FPx = t57;
                                FPy = t60;
                            } else {
                                if (-t51 < VAR(eMod_radius)) {
                                    if (0.0 >= t52) {
                                        FPx = t70;
                                        FPy = t72;
                                    } else {
                                        FPx = t64;
                                        FPy = t66;
                                    }
                                } else {
                                    FPx = t57;
                                    FPy = t60;
                                }
                            }
                        }
                    }
                }
            } else {
                if (FTx > 1.0) {
                    if (FTy >= 0.0) {
                        if (VAR(eMod_radius) <= t8) {
                            FPx = t43;
                            FPy = t45;
                        } else {
                            if (-t8 < VAR(eMod_radius)) {
                                if (0.0 >= t41) {
                                    FPx = t48;
                                    FPy = t49;
                                } else {
                                    FPx = t46;
                                    FPy = t47;
                                }
                            } else {
                                FPx = t43;
                                FPy = t45;
                            }
                        }
                    } else {
                        if (VAR(eMod_radius) <= t8) {
                            FPx = t43;
                            FPy = t45;
                        } else {
                            if (-t8 < VAR(eMod_radius)) {
                                if (0.0 >= t41) {
                                    FPx = t48;
                                    FPy = t49;
                                } else {
                                    FPx = t46;
                                    FPy = t47;
                                }
                            } else {
                                FPx = t43;
                                FPy = t45;
                            }
                        }
                    }
                } else {
                    if (-1.0 > FTx) {
                        if (FTy >= 0.0) {
                            if (VAR(eMod_radius) <= t8) {
                                FPx = t34;
                                FPy = t36;
                            } else {
                                if (-t8 < VAR(eMod_radius)) {
                                    if (0.0 >= t32) {
                                        FPx = t39;
                                        FPy = t40;
                                    } else {
                                        FPx = t37;
                                        FPy = t38;
                                    }
                                } else {
                                    FPx = t34;
                                    FPy = t36;
                                }
                            }
                        } else {
                            if (VAR(eMod_radius) <= t8) {
                                FPx = t34;
                                FPy = t36;
                            } else {
                                if (-t8 < VAR(eMod_radius)) {
                                    if (0.0 >= t32) {
                                        FPx = t39;
                                        FPy = t40;
                                    } else {
                                        FPx = t37;
                                        FPy = t38;
                                    }
                                } else {
                                    FPx = t34;
                                    FPy = t36;
                                }
                            }
                        }
                    } else {
                        if (FTy >= 0.0) {
                            if (VAR(eMod_radius) <= t8) {
                                FPx = t14;
                                FPy = t17;
                            } else {
                                if (-t8 < VAR(eMod_radius)) {
                                    if (0.0 >= t9) {
                                        FPx = t29;
                                        FPy = t31;
                                    } else {
                                        FPx = t23;
                                        FPy = t25;
                                    }
                                } else {
                                    FPx = t14;
                                    FPy = t17;
                                }
                            }
                        } else {
                            if (VAR(eMod_radius) <= t8) {
                                FPx = t14;
                                FPy = t17;
                            } else {
                                if (-t8 < VAR(eMod_radius)) {
                                    if (0.0 >= t9) {
                                        FPx = t29;
                                        FPy = t31;
                                    } else {
                                        FPx = t23;
                                        FPy = t25;
                                    }
                                } else {
                                    FPx = t14;
                                    FPy = t17;
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