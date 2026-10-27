/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        cubic3D.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from cubic3D.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double cubic3D_xpand;
    double cubic3D_style;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("cubic3D");
APO_VARIABLES(
    VAR_REAL(cubic3D_xpand, 0.25),
    VAR_REAL(cubic3D_style, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = 0.25 * (VAR(cubic3D_style) - 1.0) + 1.0;
    double t2 = 1.0 - cos(atan2(FTx, FTz));
    double t3 = 1.0 - t2 * t1;
    double t4 = VVAR + VVAR;
    double t5 = FTx * t4;
    double t6 = 0.5 * sqrt(VAR(cubic3D_xpand));
    double t7 = t5 * t6;
    double t8 = 1.0 - t6;
    double t9 = t8 * t4;
    double t10 = t9 * FPx;
    double t11 = t3 * t7 + (FPx - t10 * t3);
    double t12 = 0.5 * VVAR;
    double t13 = t11 + t12;
    double t14 = t9 * FPy;
    double t15 = 1.0 - sin(atan2(FTy, FTz));
    double t16 = 1.0 - t15 * t1;
    double t17 = FTy * t4;
    double t18 = t17 * t6;
    double t19 = (FPy - t14 * t16) + t18 * t16;
    double t20 = t19 + t12;
    double t21 = t9 * FPz;
    double t22 = t16 + t3;
    double t23 = 1.0 - t1 * (1.0 - 0.5 * (t22 * t1));
    double t24 = t4 * FTz;
    double t25 = t6 * t24;
    double t26 = (FPz - t21 * t23) + t23 * t25;
    double t27 = t26 + t12;
    double t28 = t11 - t12;
    double t29 = t19 - t12;
    double t30 = t26 - t12;
    double t31 = 1.0 - t1 * (1.0 - 0.5 * t22);
    double t32 = (FPz - t21 * t31) + t31 * t25;
    double t33 = t32 + t12;
    double t34 = t32 - t12;
    double t35 = 0.25 * (VAR(cubic3D_style) + 1.0) - 1.0;
    double t36 = 1.0 - t2 * t35;
    double t37 = t36 * t7 + (FPx - t10 * t36);
    double t38 = t37 + t12;
    double t39 = 1.0 - t15 * t35;
    double t40 = (FPy - t14 * t39) + t18 * t39;
    double t41 = t40 + t12;
    double t42 = t39 + t36;
    double t43 = 1.0 - t35 * (1.0 - 0.5 * (t42 * t35));
    double t44 = (FPz - t21 * t43) + t43 * t25;
    double t45 = t44 + t12;
    double t46 = t37 - t12;
    double t47 = t40 - t12;
    double t48 = t44 - t12;
    double t49 = 1.0 - t35 * (1.0 - 0.5 * t42);
    double t50 = (FPz - t21 * t49) + t49 * t25;
    double t51 = t50 + t12;
    double t52 = t50 - t12;
    double t53 = 1.0 - t2 * VAR(cubic3D_style);
    double t54 = t53 * t7 + (FPx - t10 * t53);
    double t55 = t54 + t12;
    double t56 = 1.0 - t15 * VAR(cubic3D_style);
    double t57 = (FPy - t14 * t56) + t18 * t56;
    double t58 = t57 + t12;
    double t59 = t56 + t53;
    double t60 = 1.0 - VAR(cubic3D_style) * (1.0 - 0.5 * (t59 * VAR(cubic3D_style)));
    double t61 = (FPz - t21 * t60) + t60 * t25;
    double t62 = t61 + t12;
    double t63 = t54 - t12;
    double t64 = t57 - t12;
    double t65 = t61 - t12;
    double t66 = 1.0 - VAR(cubic3D_style) * (1.0 - 0.5 * t59);
    double t67 = (FPz - t21 * t66) + t66 * t25;
    double t68 = t67 + t12;
    double t69 = t67 - t12;
    double t70 = FTx * t6;
    double t71 = t8 * FPx;
    double t72 = t3 * t70 + (FPx - t71 * t3);
    double t73 = t72 + t12;
    double t74 = t8 * FPy;
    double t75 = FTy * t6;
    double t76 = (FPy - t74 * t16) + t75 * t16;
    double t77 = t76 + t12;
    double t78 = t8 * FPz;
    double t79 = t6 * FTz;
    double t80 = (FPz - t78 * t23) + t23 * t79;
    double t81 = t80 + t12;
    double t82 = t72 - t12;
    double t83 = t76 - t12;
    double t84 = t80 - t12;
    double t85 = (FPz - t78 * t31) + t31 * t79;
    double t86 = t85 + t12;
    double t87 = t85 - t12;
    double t88 = t36 * t70 + (FPx - t71 * t36);
    double t89 = t88 + t12;
    double t90 = (FPy - t74 * t39) + t75 * t39;
    double t91 = t90 + t12;
    double t92 = (FPz - t78 * t43) + t43 * t79;
    double t93 = t92 + t12;
    double t94 = t88 - t12;
    double t95 = t90 - t12;
    double t96 = t92 - t12;
    double t97 = (FPz - t78 * t49) + t49 * t79;
    double t98 = t97 + t12;
    double t99 = t97 - t12;
    double t100 = t53 * t70 + (FPx - t71 * t53);
    double t101 = t100 + t12;
    double t102 = (FPy - t74 * t56) + t75 * t56;
    double t103 = t102 + t12;
    double t104 = (FPz - t78 * t60) + t60 * t79;
    double t105 = t104 + t12;
    double t106 = t100 - t12;
    double t107 = t102 - t12;
    double t108 = t104 - t12;
    double t109 = (FPz - t78 * t66) + t66 * t79;
    double t110 = t109 + t12;
    double t111 = t109 - t12;
    double t112 = 0.5 * VAR(cubic3D_xpand);
    double t113 = t5 * t112;
    double t114 = 1.0 - t112;
    double t115 = t114 * t4;
    double t116 = t115 * FPx;
    double t117 = t3 * t113 + (FPx - t116 * t3);
    double t118 = t117 + t12;
    double t119 = t115 * FPy;
    double t120 = t17 * t112;
    double t121 = (FPy - t119 * t16) + t120 * t16;
    double t122 = t121 + t12;
    double t123 = t115 * FPz;
    double t124 = t112 * t24;
    double t125 = (FPz - t123 * t23) + t23 * t124;
    double t126 = t125 + t12;
    double t127 = t117 - t12;
    double t128 = t121 - t12;
    double t129 = t125 - t12;
    double t130 = (FPz - t123 * t31) + t31 * t124;
    double t131 = t130 + t12;
    double t132 = t130 - t12;
    double t133 = t36 * t113 + (FPx - t116 * t36);
    double t134 = t133 + t12;
    double t135 = (FPy - t119 * t39) + t120 * t39;
    double t136 = t135 + t12;
    double t137 = (FPz - t123 * t43) + t43 * t124;
    double t138 = t137 + t12;
    double t139 = t133 - t12;
    double t140 = t135 - t12;
    double t141 = t137 - t12;
    double t142 = (FPz - t123 * t49) + t49 * t124;
    double t143 = t142 + t12;
    double t144 = t142 - t12;
    double t145 = t53 * t113 + (FPx - t116 * t53);
    double t146 = t145 + t12;
    double t147 = (FPy - t119 * t56) + t120 * t56;
    double t148 = t147 + t12;
    double t149 = (FPz - t123 * t60) + t60 * t124;
    double t150 = t149 + t12;
    double t151 = t145 - t12;
    double t152 = t147 - t12;
    double t153 = t149 - t12;
    double t154 = (FPz - t123 * t66) + t66 * t124;
    double t155 = t154 + t12;
    double t156 = t154 - t12;
    double t157 = FTx * t112;
    double t158 = t114 * FPx;
    double t159 = t3 * t157 + (FPx - t158 * t3);
    double t160 = t159 + t12;
    double t161 = t114 * FPy;
    double t162 = FTy * t112;
    double t163 = (FPy - t161 * t16) + t162 * t16;
    double t164 = t163 + t12;
    double t165 = t114 * FPz;
    double t166 = t112 * FTz;
    double t167 = (FPz - t165 * t23) + t23 * t166;
    double t168 = t167 + t12;
    double t169 = t159 - t12;
    double t170 = t163 - t12;
    double t171 = t167 - t12;
    double t172 = (FPz - t165 * t31) + t31 * t166;
    double t173 = t172 + t12;
    double t174 = t172 - t12;
    double t175 = t36 * t157 + (FPx - t158 * t36);
    double t176 = t175 + t12;
    double t177 = (FPy - t161 * t39) + t162 * t39;
    double t178 = t177 + t12;
    double t179 = (FPz - t165 * t43) + t43 * t166;
    double t180 = t179 + t12;
    double t181 = t175 - t12;
    double t182 = t177 - t12;
    double t183 = t179 - t12;
    double t184 = (FPz - t165 * t49) + t49 * t166;
    double t185 = t184 + t12;
    double t186 = t184 - t12;
    double t187 = t53 * t157 + (FPx - t158 * t53);
    double t188 = t187 + t12;
    double t189 = (FPy - t161 * t56) + t162 * t56;
    double t190 = t189 + t12;
    double t191 = (FPz - t165 * t60) + t60 * t166;
    double t192 = t191 + t12;
    double t193 = t187 - t12;
    double t194 = t189 - t12;
    double t195 = t191 - t12;
    double t196 = (FPz - t165 * t66) + t66 * t166;
    double t197 = t196 + t12;
    double t198 = t196 - t12;
    if (!(fabs(VAR(cubic3D_xpand)) > 1.0)) {
        if (fabs(VVAR) > 0.5) {
            if (!(fabs(VAR(cubic3D_style)) > 1.0)) {
                if (!(VAR(cubic3D_style) > 1.0)) {
                    if ((int)trunc(8.0 * random01()) != 0) {
                        if ((int)trunc(8.0 * random01()) == 1) {
                            FPx = t188;
                            FPy = t194;
                            FPz = t197;
                        } else {
                            if ((int)trunc(8.0 * random01()) == 2) {
                                FPx = t188;
                                FPy = t190;
                                FPz = t198;
                            } else {
                                if ((int)trunc(8.0 * random01()) == 3) {
                                    FPx = t188;
                                    FPy = t194;
                                    FPz = t198;
                                } else {
                                    if ((int)trunc(8.0 * random01()) == 4) {
                                        FPx = t193;
                                        FPy = t190;
                                        FPz = t197;
                                    } else {
                                        if ((int)trunc(8.0 * random01()) == 5) {
                                            FPx = t193;
                                            FPy = t194;
                                            FPz = t197;
                                        } else {
                                            if ((int)trunc(8.0 * random01()) == 6) {
                                                FPx = t193;
                                                FPy = t190;
                                                FPz = t198;
                                            } else {
                                                if ((int)trunc(8.0 * random01()) != 7) {
                                                } else {
                                                    FPx = t193;
                                                    FPy = t194;
                                                    FPz = t198;
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    } else {
                        FPx = t188;
                        FPy = t190;
                        FPz = t197;
                    }
                } else {
                    if ((int)trunc(8.0 * random01()) != 0) {
                        if ((int)trunc(8.0 * random01()) == 1) {
                            FPx = t188;
                            FPy = t194;
                            FPz = t192;
                        } else {
                            if ((int)trunc(8.0 * random01()) == 2) {
                                FPx = t188;
                                FPy = t190;
                                FPz = t195;
                            } else {
                                if ((int)trunc(8.0 * random01()) == 3) {
                                    FPx = t188;
                                    FPy = t194;
                                    FPz = t195;
                                } else {
                                    if ((int)trunc(8.0 * random01()) == 4) {
                                        FPx = t193;
                                        FPy = t190;
                                        FPz = t192;
                                    } else {
                                        if ((int)trunc(8.0 * random01()) == 5) {
                                            FPx = t193;
                                            FPy = t194;
                                            FPz = t192;
                                        } else {
                                            if ((int)trunc(8.0 * random01()) == 6) {
                                                FPx = t193;
                                                FPy = t190;
                                                FPz = t195;
                                            } else {
                                                if ((int)trunc(8.0 * random01()) != 7) {
                                                } else {
                                                    FPx = t193;
                                                    FPy = t194;
                                                    FPz = t195;
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    } else {
                        FPx = t188;
                        FPy = t190;
                        FPz = t192;
                    }
                }
            } else {
                if (!(VAR(cubic3D_style) > 1.0)) {
                    if (!(t35 > 1.0)) {
                        if ((int)trunc(8.0 * random01()) != 0) {
                            if ((int)trunc(8.0 * random01()) == 1) {
                                FPx = t176;
                                FPy = t182;
                                FPz = t185;
                            } else {
                                if ((int)trunc(8.0 * random01()) == 2) {
                                    FPx = t176;
                                    FPy = t178;
                                    FPz = t186;
                                } else {
                                    if ((int)trunc(8.0 * random01()) == 3) {
                                        FPx = t176;
                                        FPy = t182;
                                        FPz = t186;
                                    } else {
                                        if ((int)trunc(8.0 * random01()) == 4) {
                                            FPx = t181;
                                            FPy = t178;
                                            FPz = t185;
                                        } else {
                                            if ((int)trunc(8.0 * random01()) == 5) {
                                                FPx = t181;
                                                FPy = t182;
                                                FPz = t185;
                                            } else {
                                                if ((int)trunc(8.0 * random01()) == 6) {
                                                    FPx = t181;
                                                    FPy = t178;
                                                    FPz = t186;
                                                } else {
                                                    if ((int)trunc(8.0 * random01()) != 7) {
                                                    } else {
                                                        FPx = t181;
                                                        FPy = t182;
                                                        FPz = t186;
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        } else {
                            FPx = t176;
                            FPy = t178;
                            FPz = t185;
                        }
                    } else {
                        if ((int)trunc(8.0 * random01()) != 0) {
                            if ((int)trunc(8.0 * random01()) == 1) {
                                FPx = t176;
                                FPy = t182;
                                FPz = t180;
                            } else {
                                if ((int)trunc(8.0 * random01()) == 2) {
                                    FPx = t176;
                                    FPy = t178;
                                    FPz = t183;
                                } else {
                                    if ((int)trunc(8.0 * random01()) == 3) {
                                        FPx = t176;
                                        FPy = t182;
                                        FPz = t183;
                                    } else {
                                        if ((int)trunc(8.0 * random01()) == 4) {
                                            FPx = t181;
                                            FPy = t178;
                                            FPz = t180;
                                        } else {
                                            if ((int)trunc(8.0 * random01()) == 5) {
                                                FPx = t181;
                                                FPy = t182;
                                                FPz = t180;
                                            } else {
                                                if ((int)trunc(8.0 * random01()) == 6) {
                                                    FPx = t181;
                                                    FPy = t178;
                                                    FPz = t183;
                                                } else {
                                                    if ((int)trunc(8.0 * random01()) != 7) {
                                                    } else {
                                                        FPx = t181;
                                                        FPy = t182;
                                                        FPz = t183;
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        } else {
                            FPx = t176;
                            FPy = t178;
                            FPz = t180;
                        }
                    }
                } else {
                    if (!(t1 > 1.0)) {
                        if ((int)trunc(8.0 * random01()) != 0) {
                            if ((int)trunc(8.0 * random01()) == 1) {
                                FPx = t160;
                                FPy = t170;
                                FPz = t173;
                            } else {
                                if ((int)trunc(8.0 * random01()) == 2) {
                                    FPx = t160;
                                    FPy = t164;
                                    FPz = t174;
                                } else {
                                    if ((int)trunc(8.0 * random01()) == 3) {
                                        FPx = t160;
                                        FPy = t170;
                                        FPz = t174;
                                    } else {
                                        if ((int)trunc(8.0 * random01()) == 4) {
                                            FPx = t169;
                                            FPy = t164;
                                            FPz = t173;
                                        } else {
                                            if ((int)trunc(8.0 * random01()) == 5) {
                                                FPx = t169;
                                                FPy = t170;
                                                FPz = t173;
                                            } else {
                                                if ((int)trunc(8.0 * random01()) == 6) {
                                                    FPx = t169;
                                                    FPy = t164;
                                                    FPz = t174;
                                                } else {
                                                    if ((int)trunc(8.0 * random01()) != 7) {
                                                    } else {
                                                        FPx = t169;
                                                        FPy = t170;
                                                        FPz = t174;
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        } else {
                            FPx = t160;
                            FPy = t164;
                            FPz = t173;
                        }
                    } else {
                        if ((int)trunc(8.0 * random01()) != 0) {
                            if ((int)trunc(8.0 * random01()) == 1) {
                                FPx = t160;
                                FPy = t170;
                                FPz = t168;
                            } else {
                                if ((int)trunc(8.0 * random01()) == 2) {
                                    FPx = t160;
                                    FPy = t164;
                                    FPz = t171;
                                } else {
                                    if ((int)trunc(8.0 * random01()) == 3) {
                                        FPx = t160;
                                        FPy = t170;
                                        FPz = t171;
                                    } else {
                                        if ((int)trunc(8.0 * random01()) == 4) {
                                            FPx = t169;
                                            FPy = t164;
                                            FPz = t168;
                                        } else {
                                            if ((int)trunc(8.0 * random01()) == 5) {
                                                FPx = t169;
                                                FPy = t170;
                                                FPz = t168;
                                            } else {
                                                if ((int)trunc(8.0 * random01()) == 6) {
                                                    FPx = t169;
                                                    FPy = t164;
                                                    FPz = t171;
                                                } else {
                                                    if ((int)trunc(8.0 * random01()) != 7) {
                                                    } else {
                                                        FPx = t169;
                                                        FPy = t170;
                                                        FPz = t171;
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        } else {
                            FPx = t160;
                            FPy = t164;
                            FPz = t168;
                        }
                    }
                }
            }
        } else {
            if (!(fabs(VAR(cubic3D_style)) > 1.0)) {
                if (!(VAR(cubic3D_style) > 1.0)) {
                    if ((int)trunc(8.0 * random01()) != 0) {
                        if ((int)trunc(8.0 * random01()) == 1) {
                            FPx = t146;
                            FPy = t152;
                            FPz = t155;
                        } else {
                            if ((int)trunc(8.0 * random01()) == 2) {
                                FPx = t146;
                                FPy = t148;
                                FPz = t156;
                            } else {
                                if ((int)trunc(8.0 * random01()) == 3) {
                                    FPx = t146;
                                    FPy = t152;
                                    FPz = t156;
                                } else {
                                    if ((int)trunc(8.0 * random01()) == 4) {
                                        FPx = t151;
                                        FPy = t148;
                                        FPz = t155;
                                    } else {
                                        if ((int)trunc(8.0 * random01()) == 5) {
                                            FPx = t151;
                                            FPy = t152;
                                            FPz = t155;
                                        } else {
                                            if ((int)trunc(8.0 * random01()) == 6) {
                                                FPx = t151;
                                                FPy = t148;
                                                FPz = t156;
                                            } else {
                                                if ((int)trunc(8.0 * random01()) != 7) {
                                                } else {
                                                    FPx = t151;
                                                    FPy = t152;
                                                    FPz = t156;
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    } else {
                        FPx = t146;
                        FPy = t148;
                        FPz = t155;
                    }
                } else {
                    if ((int)trunc(8.0 * random01()) != 0) {
                        if ((int)trunc(8.0 * random01()) == 1) {
                            FPx = t146;
                            FPy = t152;
                            FPz = t150;
                        } else {
                            if ((int)trunc(8.0 * random01()) == 2) {
                                FPx = t146;
                                FPy = t148;
                                FPz = t153;
                            } else {
                                if ((int)trunc(8.0 * random01()) == 3) {
                                    FPx = t146;
                                    FPy = t152;
                                    FPz = t153;
                                } else {
                                    if ((int)trunc(8.0 * random01()) == 4) {
                                        FPx = t151;
                                        FPy = t148;
                                        FPz = t150;
                                    } else {
                                        if ((int)trunc(8.0 * random01()) == 5) {
                                            FPx = t151;
                                            FPy = t152;
                                            FPz = t150;
                                        } else {
                                            if ((int)trunc(8.0 * random01()) == 6) {
                                                FPx = t151;
                                                FPy = t148;
                                                FPz = t153;
                                            } else {
                                                if ((int)trunc(8.0 * random01()) != 7) {
                                                } else {
                                                    FPx = t151;
                                                    FPy = t152;
                                                    FPz = t153;
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    } else {
                        FPx = t146;
                        FPy = t148;
                        FPz = t150;
                    }
                }
            } else {
                if (!(VAR(cubic3D_style) > 1.0)) {
                    if (!(t35 > 1.0)) {
                        if ((int)trunc(8.0 * random01()) != 0) {
                            if ((int)trunc(8.0 * random01()) == 1) {
                                FPx = t134;
                                FPy = t140;
                                FPz = t143;
                            } else {
                                if ((int)trunc(8.0 * random01()) == 2) {
                                    FPx = t134;
                                    FPy = t136;
                                    FPz = t144;
                                } else {
                                    if ((int)trunc(8.0 * random01()) == 3) {
                                        FPx = t134;
                                        FPy = t140;
                                        FPz = t144;
                                    } else {
                                        if ((int)trunc(8.0 * random01()) == 4) {
                                            FPx = t139;
                                            FPy = t136;
                                            FPz = t143;
                                        } else {
                                            if ((int)trunc(8.0 * random01()) == 5) {
                                                FPx = t139;
                                                FPy = t140;
                                                FPz = t143;
                                            } else {
                                                if ((int)trunc(8.0 * random01()) == 6) {
                                                    FPx = t139;
                                                    FPy = t136;
                                                    FPz = t144;
                                                } else {
                                                    if ((int)trunc(8.0 * random01()) != 7) {
                                                    } else {
                                                        FPx = t139;
                                                        FPy = t140;
                                                        FPz = t144;
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        } else {
                            FPx = t134;
                            FPy = t136;
                            FPz = t143;
                        }
                    } else {
                        if ((int)trunc(8.0 * random01()) != 0) {
                            if ((int)trunc(8.0 * random01()) == 1) {
                                FPx = t134;
                                FPy = t140;
                                FPz = t138;
                            } else {
                                if ((int)trunc(8.0 * random01()) == 2) {
                                    FPx = t134;
                                    FPy = t136;
                                    FPz = t141;
                                } else {
                                    if ((int)trunc(8.0 * random01()) == 3) {
                                        FPx = t134;
                                        FPy = t140;
                                        FPz = t141;
                                    } else {
                                        if ((int)trunc(8.0 * random01()) == 4) {
                                            FPx = t139;
                                            FPy = t136;
                                            FPz = t138;
                                        } else {
                                            if ((int)trunc(8.0 * random01()) == 5) {
                                                FPx = t139;
                                                FPy = t140;
                                                FPz = t138;
                                            } else {
                                                if ((int)trunc(8.0 * random01()) == 6) {
                                                    FPx = t139;
                                                    FPy = t136;
                                                    FPz = t141;
                                                } else {
                                                    if ((int)trunc(8.0 * random01()) != 7) {
                                                    } else {
                                                        FPx = t139;
                                                        FPy = t140;
                                                        FPz = t141;
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        } else {
                            FPx = t134;
                            FPy = t136;
                            FPz = t138;
                        }
                    }
                } else {
                    if (!(t1 > 1.0)) {
                        if ((int)trunc(8.0 * random01()) != 0) {
                            if ((int)trunc(8.0 * random01()) == 1) {
                                FPx = t118;
                                FPy = t128;
                                FPz = t131;
                            } else {
                                if ((int)trunc(8.0 * random01()) == 2) {
                                    FPx = t118;
                                    FPy = t122;
                                    FPz = t132;
                                } else {
                                    if ((int)trunc(8.0 * random01()) == 3) {
                                        FPx = t118;
                                        FPy = t128;
                                        FPz = t132;
                                    } else {
                                        if ((int)trunc(8.0 * random01()) == 4) {
                                            FPx = t127;
                                            FPy = t122;
                                            FPz = t131;
                                        } else {
                                            if ((int)trunc(8.0 * random01()) == 5) {
                                                FPx = t127;
                                                FPy = t128;
                                                FPz = t131;
                                            } else {
                                                if ((int)trunc(8.0 * random01()) == 6) {
                                                    FPx = t127;
                                                    FPy = t122;
                                                    FPz = t132;
                                                } else {
                                                    if ((int)trunc(8.0 * random01()) != 7) {
                                                    } else {
                                                        FPx = t127;
                                                        FPy = t128;
                                                        FPz = t132;
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        } else {
                            FPx = t118;
                            FPy = t122;
                            FPz = t131;
                        }
                    } else {
                        if ((int)trunc(8.0 * random01()) != 0) {
                            if ((int)trunc(8.0 * random01()) == 1) {
                                FPx = t118;
                                FPy = t128;
                                FPz = t126;
                            } else {
                                if ((int)trunc(8.0 * random01()) == 2) {
                                    FPx = t118;
                                    FPy = t122;
                                    FPz = t129;
                                } else {
                                    if ((int)trunc(8.0 * random01()) == 3) {
                                        FPx = t118;
                                        FPy = t128;
                                        FPz = t129;
                                    } else {
                                        if ((int)trunc(8.0 * random01()) == 4) {
                                            FPx = t127;
                                            FPy = t122;
                                            FPz = t126;
                                        } else {
                                            if ((int)trunc(8.0 * random01()) == 5) {
                                                FPx = t127;
                                                FPy = t128;
                                                FPz = t126;
                                            } else {
                                                if ((int)trunc(8.0 * random01()) == 6) {
                                                    FPx = t127;
                                                    FPy = t122;
                                                    FPz = t129;
                                                } else {
                                                    if ((int)trunc(8.0 * random01()) != 7) {
                                                    } else {
                                                        FPx = t127;
                                                        FPy = t128;
                                                        FPz = t129;
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        } else {
                            FPx = t118;
                            FPy = t122;
                            FPz = t126;
                        }
                    }
                }
            }
        }
    } else {
        if (fabs(VVAR) > 0.5) {
            if (!(fabs(VAR(cubic3D_style)) > 1.0)) {
                if (!(VAR(cubic3D_style) > 1.0)) {
                    if ((int)trunc(8.0 * random01()) != 0) {
                        if ((int)trunc(8.0 * random01()) == 1) {
                            FPx = t101;
                            FPy = t107;
                            FPz = t110;
                        } else {
                            if ((int)trunc(8.0 * random01()) == 2) {
                                FPx = t101;
                                FPy = t103;
                                FPz = t111;
                            } else {
                                if ((int)trunc(8.0 * random01()) == 3) {
                                    FPx = t101;
                                    FPy = t107;
                                    FPz = t111;
                                } else {
                                    if ((int)trunc(8.0 * random01()) == 4) {
                                        FPx = t106;
                                        FPy = t103;
                                        FPz = t110;
                                    } else {
                                        if ((int)trunc(8.0 * random01()) == 5) {
                                            FPx = t106;
                                            FPy = t107;
                                            FPz = t110;
                                        } else {
                                            if ((int)trunc(8.0 * random01()) == 6) {
                                                FPx = t106;
                                                FPy = t103;
                                                FPz = t111;
                                            } else {
                                                if ((int)trunc(8.0 * random01()) != 7) {
                                                } else {
                                                    FPx = t106;
                                                    FPy = t107;
                                                    FPz = t111;
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    } else {
                        FPx = t101;
                        FPy = t103;
                        FPz = t110;
                    }
                } else {
                    if ((int)trunc(8.0 * random01()) != 0) {
                        if ((int)trunc(8.0 * random01()) == 1) {
                            FPx = t101;
                            FPy = t107;
                            FPz = t105;
                        } else {
                            if ((int)trunc(8.0 * random01()) == 2) {
                                FPx = t101;
                                FPy = t103;
                                FPz = t108;
                            } else {
                                if ((int)trunc(8.0 * random01()) == 3) {
                                    FPx = t101;
                                    FPy = t107;
                                    FPz = t108;
                                } else {
                                    if ((int)trunc(8.0 * random01()) == 4) {
                                        FPx = t106;
                                        FPy = t103;
                                        FPz = t105;
                                    } else {
                                        if ((int)trunc(8.0 * random01()) == 5) {
                                            FPx = t106;
                                            FPy = t107;
                                            FPz = t105;
                                        } else {
                                            if ((int)trunc(8.0 * random01()) == 6) {
                                                FPx = t106;
                                                FPy = t103;
                                                FPz = t108;
                                            } else {
                                                if ((int)trunc(8.0 * random01()) != 7) {
                                                } else {
                                                    FPx = t106;
                                                    FPy = t107;
                                                    FPz = t108;
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    } else {
                        FPx = t101;
                        FPy = t103;
                        FPz = t105;
                    }
                }
            } else {
                if (!(VAR(cubic3D_style) > 1.0)) {
                    if (!(t35 > 1.0)) {
                        if ((int)trunc(8.0 * random01()) != 0) {
                            if ((int)trunc(8.0 * random01()) == 1) {
                                FPx = t89;
                                FPy = t95;
                                FPz = t98;
                            } else {
                                if ((int)trunc(8.0 * random01()) == 2) {
                                    FPx = t89;
                                    FPy = t91;
                                    FPz = t99;
                                } else {
                                    if ((int)trunc(8.0 * random01()) == 3) {
                                        FPx = t89;
                                        FPy = t95;
                                        FPz = t99;
                                    } else {
                                        if ((int)trunc(8.0 * random01()) == 4) {
                                            FPx = t94;
                                            FPy = t91;
                                            FPz = t98;
                                        } else {
                                            if ((int)trunc(8.0 * random01()) == 5) {
                                                FPx = t94;
                                                FPy = t95;
                                                FPz = t98;
                                            } else {
                                                if ((int)trunc(8.0 * random01()) == 6) {
                                                    FPx = t94;
                                                    FPy = t91;
                                                    FPz = t99;
                                                } else {
                                                    if ((int)trunc(8.0 * random01()) != 7) {
                                                    } else {
                                                        FPx = t94;
                                                        FPy = t95;
                                                        FPz = t99;
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        } else {
                            FPx = t89;
                            FPy = t91;
                            FPz = t98;
                        }
                    } else {
                        if ((int)trunc(8.0 * random01()) != 0) {
                            if ((int)trunc(8.0 * random01()) == 1) {
                                FPx = t89;
                                FPy = t95;
                                FPz = t93;
                            } else {
                                if ((int)trunc(8.0 * random01()) == 2) {
                                    FPx = t89;
                                    FPy = t91;
                                    FPz = t96;
                                } else {
                                    if ((int)trunc(8.0 * random01()) == 3) {
                                        FPx = t89;
                                        FPy = t95;
                                        FPz = t96;
                                    } else {
                                        if ((int)trunc(8.0 * random01()) == 4) {
                                            FPx = t94;
                                            FPy = t91;
                                            FPz = t93;
                                        } else {
                                            if ((int)trunc(8.0 * random01()) == 5) {
                                                FPx = t94;
                                                FPy = t95;
                                                FPz = t93;
                                            } else {
                                                if ((int)trunc(8.0 * random01()) == 6) {
                                                    FPx = t94;
                                                    FPy = t91;
                                                    FPz = t96;
                                                } else {
                                                    if ((int)trunc(8.0 * random01()) != 7) {
                                                    } else {
                                                        FPx = t94;
                                                        FPy = t95;
                                                        FPz = t96;
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        } else {
                            FPx = t89;
                            FPy = t91;
                            FPz = t93;
                        }
                    }
                } else {
                    if (!(t1 > 1.0)) {
                        if ((int)trunc(8.0 * random01()) != 0) {
                            if ((int)trunc(8.0 * random01()) == 1) {
                                FPx = t73;
                                FPy = t83;
                                FPz = t86;
                            } else {
                                if ((int)trunc(8.0 * random01()) == 2) {
                                    FPx = t73;
                                    FPy = t77;
                                    FPz = t87;
                                } else {
                                    if ((int)trunc(8.0 * random01()) == 3) {
                                        FPx = t73;
                                        FPy = t83;
                                        FPz = t87;
                                    } else {
                                        if ((int)trunc(8.0 * random01()) == 4) {
                                            FPx = t82;
                                            FPy = t77;
                                            FPz = t86;
                                        } else {
                                            if ((int)trunc(8.0 * random01()) == 5) {
                                                FPx = t82;
                                                FPy = t83;
                                                FPz = t86;
                                            } else {
                                                if ((int)trunc(8.0 * random01()) == 6) {
                                                    FPx = t82;
                                                    FPy = t77;
                                                    FPz = t87;
                                                } else {
                                                    if ((int)trunc(8.0 * random01()) != 7) {
                                                    } else {
                                                        FPx = t82;
                                                        FPy = t83;
                                                        FPz = t87;
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        } else {
                            FPx = t73;
                            FPy = t77;
                            FPz = t86;
                        }
                    } else {
                        if ((int)trunc(8.0 * random01()) != 0) {
                            if ((int)trunc(8.0 * random01()) == 1) {
                                FPx = t73;
                                FPy = t83;
                                FPz = t81;
                            } else {
                                if ((int)trunc(8.0 * random01()) == 2) {
                                    FPx = t73;
                                    FPy = t77;
                                    FPz = t84;
                                } else {
                                    if ((int)trunc(8.0 * random01()) == 3) {
                                        FPx = t73;
                                        FPy = t83;
                                        FPz = t84;
                                    } else {
                                        if ((int)trunc(8.0 * random01()) == 4) {
                                            FPx = t82;
                                            FPy = t77;
                                            FPz = t81;
                                        } else {
                                            if ((int)trunc(8.0 * random01()) == 5) {
                                                FPx = t82;
                                                FPy = t83;
                                                FPz = t81;
                                            } else {
                                                if ((int)trunc(8.0 * random01()) == 6) {
                                                    FPx = t82;
                                                    FPy = t77;
                                                    FPz = t84;
                                                } else {
                                                    if ((int)trunc(8.0 * random01()) != 7) {
                                                    } else {
                                                        FPx = t82;
                                                        FPy = t83;
                                                        FPz = t84;
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        } else {
                            FPx = t73;
                            FPy = t77;
                            FPz = t81;
                        }
                    }
                }
            }
        } else {
            if (!(fabs(VAR(cubic3D_style)) > 1.0)) {
                if (!(VAR(cubic3D_style) > 1.0)) {
                    if ((int)trunc(8.0 * random01()) != 0) {
                        if ((int)trunc(8.0 * random01()) == 1) {
                            FPx = t55;
                            FPy = t64;
                            FPz = t68;
                        } else {
                            if ((int)trunc(8.0 * random01()) == 2) {
                                FPx = t55;
                                FPy = t58;
                                FPz = t69;
                            } else {
                                if ((int)trunc(8.0 * random01()) == 3) {
                                    FPx = t55;
                                    FPy = t64;
                                    FPz = t69;
                                } else {
                                    if ((int)trunc(8.0 * random01()) == 4) {
                                        FPx = t63;
                                        FPy = t58;
                                        FPz = t68;
                                    } else {
                                        if ((int)trunc(8.0 * random01()) == 5) {
                                            FPx = t63;
                                            FPy = t64;
                                            FPz = t68;
                                        } else {
                                            if ((int)trunc(8.0 * random01()) == 6) {
                                                FPx = t63;
                                                FPy = t58;
                                                FPz = t69;
                                            } else {
                                                if ((int)trunc(8.0 * random01()) != 7) {
                                                } else {
                                                    FPx = t63;
                                                    FPy = t64;
                                                    FPz = t69;
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    } else {
                        FPx = t55;
                        FPy = t58;
                        FPz = t68;
                    }
                } else {
                    if ((int)trunc(8.0 * random01()) != 0) {
                        if ((int)trunc(8.0 * random01()) == 1) {
                            FPx = t55;
                            FPy = t64;
                            FPz = t62;
                        } else {
                            if ((int)trunc(8.0 * random01()) == 2) {
                                FPx = t55;
                                FPy = t58;
                                FPz = t65;
                            } else {
                                if ((int)trunc(8.0 * random01()) == 3) {
                                    FPx = t55;
                                    FPy = t64;
                                    FPz = t65;
                                } else {
                                    if ((int)trunc(8.0 * random01()) == 4) {
                                        FPx = t63;
                                        FPy = t58;
                                        FPz = t62;
                                    } else {
                                        if ((int)trunc(8.0 * random01()) == 5) {
                                            FPx = t63;
                                            FPy = t64;
                                            FPz = t62;
                                        } else {
                                            if ((int)trunc(8.0 * random01()) == 6) {
                                                FPx = t63;
                                                FPy = t58;
                                                FPz = t65;
                                            } else {
                                                if ((int)trunc(8.0 * random01()) != 7) {
                                                } else {
                                                    FPx = t63;
                                                    FPy = t64;
                                                    FPz = t65;
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    } else {
                        FPx = t55;
                        FPy = t58;
                        FPz = t62;
                    }
                }
            } else {
                if (!(VAR(cubic3D_style) > 1.0)) {
                    if (!(t35 > 1.0)) {
                        if ((int)trunc(8.0 * random01()) != 0) {
                            if ((int)trunc(8.0 * random01()) == 1) {
                                FPx = t38;
                                FPy = t47;
                                FPz = t51;
                            } else {
                                if ((int)trunc(8.0 * random01()) == 2) {
                                    FPx = t38;
                                    FPy = t41;
                                    FPz = t52;
                                } else {
                                    if ((int)trunc(8.0 * random01()) == 3) {
                                        FPx = t38;
                                        FPy = t47;
                                        FPz = t52;
                                    } else {
                                        if ((int)trunc(8.0 * random01()) == 4) {
                                            FPx = t46;
                                            FPy = t41;
                                            FPz = t51;
                                        } else {
                                            if ((int)trunc(8.0 * random01()) == 5) {
                                                FPx = t46;
                                                FPy = t47;
                                                FPz = t51;
                                            } else {
                                                if ((int)trunc(8.0 * random01()) == 6) {
                                                    FPx = t46;
                                                    FPy = t41;
                                                    FPz = t52;
                                                } else {
                                                    if ((int)trunc(8.0 * random01()) != 7) {
                                                    } else {
                                                        FPx = t46;
                                                        FPy = t47;
                                                        FPz = t52;
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        } else {
                            FPx = t38;
                            FPy = t41;
                            FPz = t51;
                        }
                    } else {
                        if ((int)trunc(8.0 * random01()) != 0) {
                            if ((int)trunc(8.0 * random01()) == 1) {
                                FPx = t38;
                                FPy = t47;
                                FPz = t45;
                            } else {
                                if ((int)trunc(8.0 * random01()) == 2) {
                                    FPx = t38;
                                    FPy = t41;
                                    FPz = t48;
                                } else {
                                    if ((int)trunc(8.0 * random01()) == 3) {
                                        FPx = t38;
                                        FPy = t47;
                                        FPz = t48;
                                    } else {
                                        if ((int)trunc(8.0 * random01()) == 4) {
                                            FPx = t46;
                                            FPy = t41;
                                            FPz = t45;
                                        } else {
                                            if ((int)trunc(8.0 * random01()) == 5) {
                                                FPx = t46;
                                                FPy = t47;
                                                FPz = t45;
                                            } else {
                                                if ((int)trunc(8.0 * random01()) == 6) {
                                                    FPx = t46;
                                                    FPy = t41;
                                                    FPz = t48;
                                                } else {
                                                    if ((int)trunc(8.0 * random01()) != 7) {
                                                    } else {
                                                        FPx = t46;
                                                        FPy = t47;
                                                        FPz = t48;
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        } else {
                            FPx = t38;
                            FPy = t41;
                            FPz = t45;
                        }
                    }
                } else {
                    if (!(t1 > 1.0)) {
                        if ((int)trunc(8.0 * random01()) != 0) {
                            if ((int)trunc(8.0 * random01()) == 1) {
                                FPx = t13;
                                FPy = t29;
                                FPz = t33;
                            } else {
                                if ((int)trunc(8.0 * random01()) == 2) {
                                    FPx = t13;
                                    FPy = t20;
                                    FPz = t34;
                                } else {
                                    if ((int)trunc(8.0 * random01()) == 3) {
                                        FPx = t13;
                                        FPy = t29;
                                        FPz = t34;
                                    } else {
                                        if ((int)trunc(8.0 * random01()) == 4) {
                                            FPx = t28;
                                            FPy = t20;
                                            FPz = t33;
                                        } else {
                                            if ((int)trunc(8.0 * random01()) == 5) {
                                                FPx = t28;
                                                FPy = t29;
                                                FPz = t33;
                                            } else {
                                                if ((int)trunc(8.0 * random01()) == 6) {
                                                    FPx = t28;
                                                    FPy = t20;
                                                    FPz = t34;
                                                } else {
                                                    if ((int)trunc(8.0 * random01()) != 7) {
                                                    } else {
                                                        FPx = t28;
                                                        FPy = t29;
                                                        FPz = t34;
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        } else {
                            FPx = t13;
                            FPy = t20;
                            FPz = t33;
                        }
                    } else {
                        if ((int)trunc(8.0 * random01()) != 0) {
                            if ((int)trunc(8.0 * random01()) == 1) {
                                FPx = t13;
                                FPy = t29;
                                FPz = t27;
                            } else {
                                if ((int)trunc(8.0 * random01()) == 2) {
                                    FPx = t13;
                                    FPy = t20;
                                    FPz = t30;
                                } else {
                                    if ((int)trunc(8.0 * random01()) == 3) {
                                        FPx = t13;
                                        FPy = t29;
                                        FPz = t30;
                                    } else {
                                        if ((int)trunc(8.0 * random01()) == 4) {
                                            FPx = t28;
                                            FPy = t20;
                                            FPz = t27;
                                        } else {
                                            if ((int)trunc(8.0 * random01()) == 5) {
                                                FPx = t28;
                                                FPy = t29;
                                                FPz = t27;
                                            } else {
                                                if ((int)trunc(8.0 * random01()) == 6) {
                                                    FPx = t28;
                                                    FPy = t20;
                                                    FPz = t30;
                                                } else {
                                                    if ((int)trunc(8.0 * random01()) != 7) {
                                                    } else {
                                                        FPx = t28;
                                                        FPy = t29;
                                                        FPz = t30;
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        } else {
                            FPx = t13;
                            FPy = t20;
                            FPz = t27;
                        }
                    }
                }
            }
        }
    }
    return TRUE;
}