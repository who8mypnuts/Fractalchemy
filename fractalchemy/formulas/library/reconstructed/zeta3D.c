/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        zeta3D.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from zeta3D.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {

} Variables;
#include "apoplugin.h"
APO_PLUGIN("zeta3D");
APO_VARIABLES(

);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = hypot(2.0, 0.0);
    double t2 = isnan(t1);
    double t3 = isnan(FTy);
    double t4 = 0.0 * FTy + FTx;
    double t5 = atan2(0.0, 2.0);
    double t6 = t4 * t5;
    double t7 = pow(t1, t4);
    double t8 = cos(t6) * t7;
    double t9 = sin(t6) * t7;
    double t10 = t8 * t8 + t9 * t9;
    double t11 = (t8 + 0.0 * t9) / t10;
    double t12 = t11 * VVAR + FPx;
    double t13 = (0.0 * t8 - t9) / t10;
    double t14 = t13 * VVAR + FPy;
    double t15 = sqrt(t13 * t13 + t11 * t11) * VVAR + FPz;
    double t16 = hypot(FPz, 0.0);
    double t17 = isnan(t16);
    double t18 = atan2(0.0, FPz);
    double t19 = t4 * t18;
    double t20 = pow(t16, t4);
    double t21 = cos(t19) * t20;
    double t22 = sin(t19) * t20;
    double t23 = t21 * t21 + t22 * t22;
    double t24 = (0.0 * t21 - t22) / t23;
    double t25 = (t21 + 0.0 * t22) / t23;
    double t26 = sqrt(t24 * t24 + t25 * t25) * VVAR + FPz;
    double t27 = 0.0 / 0.0;
    double t28 = t27 * t27;
    double t29 = sqrt(t28 + t28) * VVAR + FPz;
    double t30 = hypot(FPy, 0.0);
    double t31 = isnan(t30);
    double t32 = atan2(0.0, FPy);
    double t33 = t4 * t32;
    double t34 = pow(t30, t4);
    double t35 = cos(t33) * t34;
    double t36 = sin(t33) * t34;
    double t37 = ((0.0 * t35 - t36) / (t35 * t35 + t36 * t36)) * VVAR + FPy;
    double t38 = t27 * VVAR;
    double t39 = t38 + FPy;
    double t40 = log(t1);
    double t41 = FTy * t40 + t6;
    double t42 = exp(t40 * t4 - FTy * t5);
    double t43 = cos(t41) * t42;
    double t44 = sin(t41) * t42;
    double t45 = t43 * t43 + t44 * t44;
    double t46 = (t43 + 0.0 * t44) / t45;
    double t47 = t46 * VVAR + FPx;
    double t48 = (0.0 * t43 - t44) / t45;
    double t49 = t48 * VVAR + FPy;
    double t50 = sqrt(t48 * t48 + t46 * t46) * VVAR + FPz;
    double t51 = log(t16);
    double t52 = FTy * t51 + t19;
    double t53 = exp(t51 * t4 - FTy * t18);
    double t54 = cos(t52) * t53;
    double t55 = sin(t52) * t53;
    double t56 = t54 * t54 + t55 * t55;
    double t57 = (0.0 * t54 - t55) / t56;
    double t58 = (t54 + 0.0 * t55) / t56;
    double t59 = sqrt(t57 * t57 + t58 * t58) * VVAR + FPz;
    double t60 = log(t30);
    double t61 = FTy * t60 + t33;
    double t62 = exp(t60 * t4 - FTy * t32);
    double t63 = cos(t61) * t62;
    double t64 = sin(t61) * t62;
    double t65 = ((0.0 * t63 - t64) / (t63 * t63 + t64 * t64)) * VVAR + FPy;
    double t66 = t38 + FPx;
    double t67 = hypot(FPx, 0.0);
    double t68 = isnan(t67);
    double t69 = atan2(0.0, FPx);
    double t70 = t4 * t69;
    double t71 = pow(t67, t4);
    double t72 = cos(t70) * t71;
    double t73 = sin(t70) * t71;
    double t74 = ((t72 + 0.0 * t73) / (t72 * t72 + t73 * t73)) * VVAR + FPx;
    double t75 = log(t67);
    double t76 = FTy * t75 + t70;
    double t77 = exp(t75 * t4 - FTy * t69);
    double t78 = cos(t76) * t77;
    double t79 = sin(t76) * t77;
    double t80 = ((t78 + 0.0 * t79) / (t78 * t78 + t79 * t79)) * VVAR + FPx;
    if (FPx >= 2.0) {
        if (t68) {
            if (FTy != 0.0) {
                if (FPy >= 2.0) {
                    if (t31) {
                        if (FPz >= 2.0) {
                            if (t17) {
                                FPx = t80;
                                FPy = t65;
                                FPz = t59;
                            } else {
                                if (t16 == 0.0) {
                                    FPx = t80;
                                    FPy = t65;
                                    FPz = t29;
                                } else {
                                    FPx = t80;
                                    FPy = t65;
                                    FPz = t59;
                                }
                            }
                        } else {
                            if (t2) {
                                FPx = t80;
                                FPy = t65;
                                FPz = t50;
                            } else {
                                if (t1 == 0.0) {
                                    FPx = t80;
                                    FPy = t65;
                                    FPz = t29;
                                } else {
                                    FPx = t80;
                                    FPy = t65;
                                    FPz = t50;
                                }
                            }
                        }
                    } else {
                        if (t30 == 0.0) {
                            if (FPz >= 2.0) {
                                if (t17) {
                                    FPx = t80;
                                    FPy = t39;
                                    FPz = t59;
                                } else {
                                    if (t16 == 0.0) {
                                        FPx = t80;
                                        FPy = t39;
                                        FPz = t29;
                                    } else {
                                        FPx = t80;
                                        FPy = t39;
                                        FPz = t59;
                                    }
                                }
                            } else {
                                if (t2) {
                                    FPx = t80;
                                    FPy = t39;
                                    FPz = t50;
                                } else {
                                    if (t1 == 0.0) {
                                        FPx = t80;
                                        FPy = t39;
                                        FPz = t29;
                                    } else {
                                        FPx = t80;
                                        FPy = t39;
                                        FPz = t50;
                                    }
                                }
                            }
                        } else {
                            if (FPz >= 2.0) {
                                if (t17) {
                                    FPx = t80;
                                    FPy = t65;
                                    FPz = t59;
                                } else {
                                    if (t16 == 0.0) {
                                        FPx = t80;
                                        FPy = t65;
                                        FPz = t29;
                                    } else {
                                        FPx = t80;
                                        FPy = t65;
                                        FPz = t59;
                                    }
                                }
                            } else {
                                if (t2) {
                                    FPx = t80;
                                    FPy = t65;
                                    FPz = t50;
                                } else {
                                    if (t1 == 0.0) {
                                        FPx = t80;
                                        FPy = t65;
                                        FPz = t29;
                                    } else {
                                        FPx = t80;
                                        FPy = t65;
                                        FPz = t50;
                                    }
                                }
                            }
                        }
                    }
                } else {
                    if (t2) {
                        if (FPz >= 2.0) {
                            if (t17) {
                                FPx = t80;
                                FPy = t49;
                                FPz = t59;
                            } else {
                                if (t16 == 0.0) {
                                    FPx = t80;
                                    FPy = t49;
                                    FPz = t29;
                                } else {
                                    FPx = t80;
                                    FPy = t49;
                                    FPz = t59;
                                }
                            }
                        } else {
                            FPx = t80;
                            FPy = t49;
                            FPz = t50;
                        }
                    } else {
                        if (t1 == 0.0) {
                            if (FPz >= 2.0) {
                                if (t17) {
                                    FPx = t80;
                                    FPy = t39;
                                    FPz = t59;
                                } else {
                                    if (t16 == 0.0) {
                                        FPx = t80;
                                        FPy = t39;
                                        FPz = t29;
                                    } else {
                                        FPx = t80;
                                        FPy = t39;
                                        FPz = t59;
                                    }
                                }
                            } else {
                                FPx = t80;
                                FPy = t39;
                                FPz = t29;
                            }
                        } else {
                            if (FPz >= 2.0) {
                                if (t17) {
                                    FPx = t80;
                                    FPy = t49;
                                    FPz = t59;
                                } else {
                                    if (t16 == 0.0) {
                                        FPx = t80;
                                        FPy = t49;
                                        FPz = t29;
                                    } else {
                                        FPx = t80;
                                        FPy = t49;
                                        FPz = t59;
                                    }
                                }
                            } else {
                                FPx = t80;
                                FPy = t49;
                                FPz = t50;
                            }
                        }
                    }
                }
            } else {
                if (t3) {
                    if (FPy >= 2.0) {
                        if (t31) {
                            if (FPz >= 2.0) {
                                if (t17) {
                                    FPx = t80;
                                    FPy = t65;
                                    FPz = t59;
                                } else {
                                    if (t16 == 0.0) {
                                        FPx = t80;
                                        FPy = t65;
                                        FPz = t29;
                                    } else {
                                        FPx = t80;
                                        FPy = t65;
                                        FPz = t59;
                                    }
                                }
                            } else {
                                if (t2) {
                                    FPx = t80;
                                    FPy = t65;
                                    FPz = t50;
                                } else {
                                    if (t1 == 0.0) {
                                        FPx = t80;
                                        FPy = t65;
                                        FPz = t29;
                                    } else {
                                        FPx = t80;
                                        FPy = t65;
                                        FPz = t50;
                                    }
                                }
                            }
                        } else {
                            if (t30 == 0.0) {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t80;
                                        FPy = t39;
                                        FPz = t59;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t80;
                                            FPy = t39;
                                            FPz = t29;
                                        } else {
                                            FPx = t80;
                                            FPy = t39;
                                            FPz = t59;
                                        }
                                    }
                                } else {
                                    if (t2) {
                                        FPx = t80;
                                        FPy = t39;
                                        FPz = t50;
                                    } else {
                                        if (t1 == 0.0) {
                                            FPx = t80;
                                            FPy = t39;
                                            FPz = t29;
                                        } else {
                                            FPx = t80;
                                            FPy = t39;
                                            FPz = t50;
                                        }
                                    }
                                }
                            } else {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t80;
                                        FPy = t65;
                                        FPz = t59;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t80;
                                            FPy = t65;
                                            FPz = t29;
                                        } else {
                                            FPx = t80;
                                            FPy = t65;
                                            FPz = t59;
                                        }
                                    }
                                } else {
                                    if (t2) {
                                        FPx = t80;
                                        FPy = t65;
                                        FPz = t50;
                                    } else {
                                        if (t1 == 0.0) {
                                            FPx = t80;
                                            FPy = t65;
                                            FPz = t29;
                                        } else {
                                            FPx = t80;
                                            FPy = t65;
                                            FPz = t50;
                                        }
                                    }
                                }
                            }
                        }
                    } else {
                        if (t2) {
                            if (FPz >= 2.0) {
                                if (t17) {
                                    FPx = t80;
                                    FPy = t49;
                                    FPz = t59;
                                } else {
                                    if (t16 == 0.0) {
                                        FPx = t80;
                                        FPy = t49;
                                        FPz = t29;
                                    } else {
                                        FPx = t80;
                                        FPy = t49;
                                        FPz = t59;
                                    }
                                }
                            } else {
                                FPx = t80;
                                FPy = t49;
                                FPz = t50;
                            }
                        } else {
                            if (t1 == 0.0) {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t80;
                                        FPy = t39;
                                        FPz = t59;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t80;
                                            FPy = t39;
                                            FPz = t29;
                                        } else {
                                            FPx = t80;
                                            FPy = t39;
                                            FPz = t59;
                                        }
                                    }
                                } else {
                                    FPx = t80;
                                    FPy = t39;
                                    FPz = t29;
                                }
                            } else {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t80;
                                        FPy = t49;
                                        FPz = t59;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t80;
                                            FPy = t49;
                                            FPz = t29;
                                        } else {
                                            FPx = t80;
                                            FPy = t49;
                                            FPz = t59;
                                        }
                                    }
                                } else {
                                    FPx = t80;
                                    FPy = t49;
                                    FPz = t50;
                                }
                            }
                        }
                    }
                } else {
                    if (FPy >= 2.0) {
                        if (t31) {
                            if (FPz >= 2.0) {
                                if (t17) {
                                    FPx = t74;
                                    FPy = t37;
                                    FPz = t26;
                                } else {
                                    if (t16 == 0.0) {
                                        FPx = t74;
                                        FPy = t37;
                                        FPz = t29;
                                    } else {
                                        FPx = t74;
                                        FPy = t37;
                                        FPz = t26;
                                    }
                                }
                            } else {
                                if (t2) {
                                    FPx = t74;
                                    FPy = t37;
                                    FPz = t15;
                                } else {
                                    if (t1 == 0.0) {
                                        FPx = t74;
                                        FPy = t37;
                                        FPz = t29;
                                    } else {
                                        FPx = t74;
                                        FPy = t37;
                                        FPz = t15;
                                    }
                                }
                            }
                        } else {
                            if (t30 == 0.0) {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t74;
                                        FPy = t39;
                                        FPz = t26;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t74;
                                            FPy = t39;
                                            FPz = t29;
                                        } else {
                                            FPx = t74;
                                            FPy = t39;
                                            FPz = t26;
                                        }
                                    }
                                } else {
                                    if (t2) {
                                        FPx = t74;
                                        FPy = t39;
                                        FPz = t15;
                                    } else {
                                        if (t1 == 0.0) {
                                            FPx = t74;
                                            FPy = t39;
                                            FPz = t29;
                                        } else {
                                            FPx = t74;
                                            FPy = t39;
                                            FPz = t15;
                                        }
                                    }
                                }
                            } else {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t74;
                                        FPy = t37;
                                        FPz = t26;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t74;
                                            FPy = t37;
                                            FPz = t29;
                                        } else {
                                            FPx = t74;
                                            FPy = t37;
                                            FPz = t26;
                                        }
                                    }
                                } else {
                                    if (t2) {
                                        FPx = t74;
                                        FPy = t37;
                                        FPz = t15;
                                    } else {
                                        if (t1 == 0.0) {
                                            FPx = t74;
                                            FPy = t37;
                                            FPz = t29;
                                        } else {
                                            FPx = t74;
                                            FPy = t37;
                                            FPz = t15;
                                        }
                                    }
                                }
                            }
                        }
                    } else {
                        if (t2) {
                            if (FPz >= 2.0) {
                                if (t17) {
                                    FPx = t74;
                                    FPy = t14;
                                    FPz = t26;
                                } else {
                                    if (t16 == 0.0) {
                                        FPx = t74;
                                        FPy = t14;
                                        FPz = t29;
                                    } else {
                                        FPx = t74;
                                        FPy = t14;
                                        FPz = t26;
                                    }
                                }
                            } else {
                                FPx = t74;
                                FPy = t14;
                                FPz = t15;
                            }
                        } else {
                            if (t1 == 0.0) {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t74;
                                        FPy = t39;
                                        FPz = t26;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t74;
                                            FPy = t39;
                                            FPz = t29;
                                        } else {
                                            FPx = t74;
                                            FPy = t39;
                                            FPz = t26;
                                        }
                                    }
                                } else {
                                    FPx = t74;
                                    FPy = t39;
                                    FPz = t29;
                                }
                            } else {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t74;
                                        FPy = t14;
                                        FPz = t26;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t74;
                                            FPy = t14;
                                            FPz = t29;
                                        } else {
                                            FPx = t74;
                                            FPy = t14;
                                            FPz = t26;
                                        }
                                    }
                                } else {
                                    FPx = t74;
                                    FPy = t14;
                                    FPz = t15;
                                }
                            }
                        }
                    }
                }
            }
        } else {
            if (t67 == 0.0) {
                if (FPy >= 2.0) {
                    if (t31) {
                        if (FTy != 0.0) {
                            if (FPz >= 2.0) {
                                if (t17) {
                                    FPx = t66;
                                    FPy = t65;
                                    FPz = t59;
                                } else {
                                    if (t16 == 0.0) {
                                        FPx = t66;
                                        FPy = t65;
                                        FPz = t29;
                                    } else {
                                        FPx = t66;
                                        FPy = t65;
                                        FPz = t59;
                                    }
                                }
                            } else {
                                if (t2) {
                                    FPx = t66;
                                    FPy = t65;
                                    FPz = t50;
                                } else {
                                    if (t1 == 0.0) {
                                        FPx = t66;
                                        FPy = t65;
                                        FPz = t29;
                                    } else {
                                        FPx = t66;
                                        FPy = t65;
                                        FPz = t50;
                                    }
                                }
                            }
                        } else {
                            if (t3) {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t66;
                                        FPy = t65;
                                        FPz = t59;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t66;
                                            FPy = t65;
                                            FPz = t29;
                                        } else {
                                            FPx = t66;
                                            FPy = t65;
                                            FPz = t59;
                                        }
                                    }
                                } else {
                                    if (t2) {
                                        FPx = t66;
                                        FPy = t65;
                                        FPz = t50;
                                    } else {
                                        if (t1 == 0.0) {
                                            FPx = t66;
                                            FPy = t65;
                                            FPz = t29;
                                        } else {
                                            FPx = t66;
                                            FPy = t65;
                                            FPz = t50;
                                        }
                                    }
                                }
                            } else {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t66;
                                        FPy = t37;
                                        FPz = t26;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t66;
                                            FPy = t37;
                                            FPz = t29;
                                        } else {
                                            FPx = t66;
                                            FPy = t37;
                                            FPz = t26;
                                        }
                                    }
                                } else {
                                    if (t2) {
                                        FPx = t66;
                                        FPy = t37;
                                        FPz = t15;
                                    } else {
                                        if (t1 == 0.0) {
                                            FPx = t66;
                                            FPy = t37;
                                            FPz = t29;
                                        } else {
                                            FPx = t66;
                                            FPy = t37;
                                            FPz = t15;
                                        }
                                    }
                                }
                            }
                        }
                    } else {
                        if (t30 == 0.0) {
                            if (FPz >= 2.0) {
                                if (t17) {
                                    if (FTy != 0.0) {
                                        FPx = t66;
                                        FPy = t39;
                                        FPz = t59;
                                    } else {
                                        if (t3) {
                                            FPx = t66;
                                            FPy = t39;
                                            FPz = t59;
                                        } else {
                                            FPx = t66;
                                            FPy = t39;
                                            FPz = t26;
                                        }
                                    }
                                } else {
                                    if (t16 == 0.0) {
                                        FPx = t66;
                                        FPy = t39;
                                        FPz = t29;
                                    } else {
                                        if (FTy != 0.0) {
                                            FPx = t66;
                                            FPy = t39;
                                            FPz = t59;
                                        } else {
                                            if (t3) {
                                                FPx = t66;
                                                FPy = t39;
                                                FPz = t59;
                                            } else {
                                                FPx = t66;
                                                FPy = t39;
                                                FPz = t26;
                                            }
                                        }
                                    }
                                }
                            } else {
                                if (t2) {
                                    if (FTy != 0.0) {
                                        FPx = t66;
                                        FPy = t39;
                                        FPz = t50;
                                    } else {
                                        if (t3) {
                                            FPx = t66;
                                            FPy = t39;
                                            FPz = t50;
                                        } else {
                                            FPx = t66;
                                            FPy = t39;
                                            FPz = t15;
                                        }
                                    }
                                } else {
                                    if (t1 == 0.0) {
                                        FPx = t66;
                                        FPy = t39;
                                        FPz = t29;
                                    } else {
                                        if (FTy != 0.0) {
                                            FPx = t66;
                                            FPy = t39;
                                            FPz = t50;
                                        } else {
                                            if (t3) {
                                                FPx = t66;
                                                FPy = t39;
                                                FPz = t50;
                                            } else {
                                                FPx = t66;
                                                FPy = t39;
                                                FPz = t15;
                                            }
                                        }
                                    }
                                }
                            }
                        } else {
                            if (FTy != 0.0) {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t66;
                                        FPy = t65;
                                        FPz = t59;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t66;
                                            FPy = t65;
                                            FPz = t29;
                                        } else {
                                            FPx = t66;
                                            FPy = t65;
                                            FPz = t59;
                                        }
                                    }
                                } else {
                                    if (t2) {
                                        FPx = t66;
                                        FPy = t65;
                                        FPz = t50;
                                    } else {
                                        if (t1 == 0.0) {
                                            FPx = t66;
                                            FPy = t65;
                                            FPz = t29;
                                        } else {
                                            FPx = t66;
                                            FPy = t65;
                                            FPz = t50;
                                        }
                                    }
                                }
                            } else {
                                if (t3) {
                                    if (FPz >= 2.0) {
                                        if (t17) {
                                            FPx = t66;
                                            FPy = t65;
                                            FPz = t59;
                                        } else {
                                            if (t16 == 0.0) {
                                                FPx = t66;
                                                FPy = t65;
                                                FPz = t29;
                                            } else {
                                                FPx = t66;
                                                FPy = t65;
                                                FPz = t59;
                                            }
                                        }
                                    } else {
                                        if (t2) {
                                            FPx = t66;
                                            FPy = t65;
                                            FPz = t50;
                                        } else {
                                            if (t1 == 0.0) {
                                                FPx = t66;
                                                FPy = t65;
                                                FPz = t29;
                                            } else {
                                                FPx = t66;
                                                FPy = t65;
                                                FPz = t50;
                                            }
                                        }
                                    }
                                } else {
                                    if (FPz >= 2.0) {
                                        if (t17) {
                                            FPx = t66;
                                            FPy = t37;
                                            FPz = t26;
                                        } else {
                                            if (t16 == 0.0) {
                                                FPx = t66;
                                                FPy = t37;
                                                FPz = t29;
                                            } else {
                                                FPx = t66;
                                                FPy = t37;
                                                FPz = t26;
                                            }
                                        }
                                    } else {
                                        if (t2) {
                                            FPx = t66;
                                            FPy = t37;
                                            FPz = t15;
                                        } else {
                                            if (t1 == 0.0) {
                                                FPx = t66;
                                                FPy = t37;
                                                FPz = t29;
                                            } else {
                                                FPx = t66;
                                                FPy = t37;
                                                FPz = t15;
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                } else {
                    if (t2) {
                        if (FTy != 0.0) {
                            if (FPz >= 2.0) {
                                if (t17) {
                                    FPx = t66;
                                    FPy = t49;
                                    FPz = t59;
                                } else {
                                    if (t16 == 0.0) {
                                        FPx = t66;
                                        FPy = t49;
                                        FPz = t29;
                                    } else {
                                        FPx = t66;
                                        FPy = t49;
                                        FPz = t59;
                                    }
                                }
                            } else {
                                FPx = t66;
                                FPy = t49;
                                FPz = t50;
                            }
                        } else {
                            if (t3) {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t66;
                                        FPy = t49;
                                        FPz = t59;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t66;
                                            FPy = t49;
                                            FPz = t29;
                                        } else {
                                            FPx = t66;
                                            FPy = t49;
                                            FPz = t59;
                                        }
                                    }
                                } else {
                                    FPx = t66;
                                    FPy = t49;
                                    FPz = t50;
                                }
                            } else {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t66;
                                        FPy = t14;
                                        FPz = t26;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t66;
                                            FPy = t14;
                                            FPz = t29;
                                        } else {
                                            FPx = t66;
                                            FPy = t14;
                                            FPz = t26;
                                        }
                                    }
                                } else {
                                    FPx = t66;
                                    FPy = t14;
                                    FPz = t15;
                                }
                            }
                        }
                    } else {
                        if (t1 == 0.0) {
                            if (FPz >= 2.0) {
                                if (t17) {
                                    if (FTy != 0.0) {
                                        FPx = t66;
                                        FPy = t39;
                                        FPz = t59;
                                    } else {
                                        if (t3) {
                                            FPx = t66;
                                            FPy = t39;
                                            FPz = t59;
                                        } else {
                                            FPx = t66;
                                            FPy = t39;
                                            FPz = t26;
                                        }
                                    }
                                } else {
                                    if (t16 == 0.0) {
                                        FPx = t66;
                                        FPy = t39;
                                        FPz = t29;
                                    } else {
                                        if (FTy != 0.0) {
                                            FPx = t66;
                                            FPy = t39;
                                            FPz = t59;
                                        } else {
                                            if (t3) {
                                                FPx = t66;
                                                FPy = t39;
                                                FPz = t59;
                                            } else {
                                                FPx = t66;
                                                FPy = t39;
                                                FPz = t26;
                                            }
                                        }
                                    }
                                }
                            } else {
                                FPx = t66;
                                FPy = t39;
                                FPz = t29;
                            }
                        } else {
                            if (FTy != 0.0) {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t66;
                                        FPy = t49;
                                        FPz = t59;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t66;
                                            FPy = t49;
                                            FPz = t29;
                                        } else {
                                            FPx = t66;
                                            FPy = t49;
                                            FPz = t59;
                                        }
                                    }
                                } else {
                                    FPx = t66;
                                    FPy = t49;
                                    FPz = t50;
                                }
                            } else {
                                if (t3) {
                                    if (FPz >= 2.0) {
                                        if (t17) {
                                            FPx = t66;
                                            FPy = t49;
                                            FPz = t59;
                                        } else {
                                            if (t16 == 0.0) {
                                                FPx = t66;
                                                FPy = t49;
                                                FPz = t29;
                                            } else {
                                                FPx = t66;
                                                FPy = t49;
                                                FPz = t59;
                                            }
                                        }
                                    } else {
                                        FPx = t66;
                                        FPy = t49;
                                        FPz = t50;
                                    }
                                } else {
                                    if (FPz >= 2.0) {
                                        if (t17) {
                                            FPx = t66;
                                            FPy = t14;
                                            FPz = t26;
                                        } else {
                                            if (t16 == 0.0) {
                                                FPx = t66;
                                                FPy = t14;
                                                FPz = t29;
                                            } else {
                                                FPx = t66;
                                                FPy = t14;
                                                FPz = t26;
                                            }
                                        }
                                    } else {
                                        FPx = t66;
                                        FPy = t14;
                                        FPz = t15;
                                    }
                                }
                            }
                        }
                    }
                }
            } else {
                if (FTy != 0.0) {
                    if (FPy >= 2.0) {
                        if (t31) {
                            if (FPz >= 2.0) {
                                if (t17) {
                                    FPx = t80;
                                    FPy = t65;
                                    FPz = t59;
                                } else {
                                    if (t16 == 0.0) {
                                        FPx = t80;
                                        FPy = t65;
                                        FPz = t29;
                                    } else {
                                        FPx = t80;
                                        FPy = t65;
                                        FPz = t59;
                                    }
                                }
                            } else {
                                if (t2) {
                                    FPx = t80;
                                    FPy = t65;
                                    FPz = t50;
                                } else {
                                    if (t1 == 0.0) {
                                        FPx = t80;
                                        FPy = t65;
                                        FPz = t29;
                                    } else {
                                        FPx = t80;
                                        FPy = t65;
                                        FPz = t50;
                                    }
                                }
                            }
                        } else {
                            if (t30 == 0.0) {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t80;
                                        FPy = t39;
                                        FPz = t59;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t80;
                                            FPy = t39;
                                            FPz = t29;
                                        } else {
                                            FPx = t80;
                                            FPy = t39;
                                            FPz = t59;
                                        }
                                    }
                                } else {
                                    if (t2) {
                                        FPx = t80;
                                        FPy = t39;
                                        FPz = t50;
                                    } else {
                                        if (t1 == 0.0) {
                                            FPx = t80;
                                            FPy = t39;
                                            FPz = t29;
                                        } else {
                                            FPx = t80;
                                            FPy = t39;
                                            FPz = t50;
                                        }
                                    }
                                }
                            } else {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t80;
                                        FPy = t65;
                                        FPz = t59;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t80;
                                            FPy = t65;
                                            FPz = t29;
                                        } else {
                                            FPx = t80;
                                            FPy = t65;
                                            FPz = t59;
                                        }
                                    }
                                } else {
                                    if (t2) {
                                        FPx = t80;
                                        FPy = t65;
                                        FPz = t50;
                                    } else {
                                        if (t1 == 0.0) {
                                            FPx = t80;
                                            FPy = t65;
                                            FPz = t29;
                                        } else {
                                            FPx = t80;
                                            FPy = t65;
                                            FPz = t50;
                                        }
                                    }
                                }
                            }
                        }
                    } else {
                        if (t2) {
                            if (FPz >= 2.0) {
                                if (t17) {
                                    FPx = t80;
                                    FPy = t49;
                                    FPz = t59;
                                } else {
                                    if (t16 == 0.0) {
                                        FPx = t80;
                                        FPy = t49;
                                        FPz = t29;
                                    } else {
                                        FPx = t80;
                                        FPy = t49;
                                        FPz = t59;
                                    }
                                }
                            } else {
                                FPx = t80;
                                FPy = t49;
                                FPz = t50;
                            }
                        } else {
                            if (t1 == 0.0) {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t80;
                                        FPy = t39;
                                        FPz = t59;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t80;
                                            FPy = t39;
                                            FPz = t29;
                                        } else {
                                            FPx = t80;
                                            FPy = t39;
                                            FPz = t59;
                                        }
                                    }
                                } else {
                                    FPx = t80;
                                    FPy = t39;
                                    FPz = t29;
                                }
                            } else {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t80;
                                        FPy = t49;
                                        FPz = t59;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t80;
                                            FPy = t49;
                                            FPz = t29;
                                        } else {
                                            FPx = t80;
                                            FPy = t49;
                                            FPz = t59;
                                        }
                                    }
                                } else {
                                    FPx = t80;
                                    FPy = t49;
                                    FPz = t50;
                                }
                            }
                        }
                    }
                } else {
                    if (t3) {
                        if (FPy >= 2.0) {
                            if (t31) {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t80;
                                        FPy = t65;
                                        FPz = t59;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t80;
                                            FPy = t65;
                                            FPz = t29;
                                        } else {
                                            FPx = t80;
                                            FPy = t65;
                                            FPz = t59;
                                        }
                                    }
                                } else {
                                    if (t2) {
                                        FPx = t80;
                                        FPy = t65;
                                        FPz = t50;
                                    } else {
                                        if (t1 == 0.0) {
                                            FPx = t80;
                                            FPy = t65;
                                            FPz = t29;
                                        } else {
                                            FPx = t80;
                                            FPy = t65;
                                            FPz = t50;
                                        }
                                    }
                                }
                            } else {
                                if (t30 == 0.0) {
                                    if (FPz >= 2.0) {
                                        if (t17) {
                                            FPx = t80;
                                            FPy = t39;
                                            FPz = t59;
                                        } else {
                                            if (t16 == 0.0) {
                                                FPx = t80;
                                                FPy = t39;
                                                FPz = t29;
                                            } else {
                                                FPx = t80;
                                                FPy = t39;
                                                FPz = t59;
                                            }
                                        }
                                    } else {
                                        if (t2) {
                                            FPx = t80;
                                            FPy = t39;
                                            FPz = t50;
                                        } else {
                                            if (t1 == 0.0) {
                                                FPx = t80;
                                                FPy = t39;
                                                FPz = t29;
                                            } else {
                                                FPx = t80;
                                                FPy = t39;
                                                FPz = t50;
                                            }
                                        }
                                    }
                                } else {
                                    if (FPz >= 2.0) {
                                        if (t17) {
                                            FPx = t80;
                                            FPy = t65;
                                            FPz = t59;
                                        } else {
                                            if (t16 == 0.0) {
                                                FPx = t80;
                                                FPy = t65;
                                                FPz = t29;
                                            } else {
                                                FPx = t80;
                                                FPy = t65;
                                                FPz = t59;
                                            }
                                        }
                                    } else {
                                        if (t2) {
                                            FPx = t80;
                                            FPy = t65;
                                            FPz = t50;
                                        } else {
                                            if (t1 == 0.0) {
                                                FPx = t80;
                                                FPy = t65;
                                                FPz = t29;
                                            } else {
                                                FPx = t80;
                                                FPy = t65;
                                                FPz = t50;
                                            }
                                        }
                                    }
                                }
                            }
                        } else {
                            if (t2) {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t80;
                                        FPy = t49;
                                        FPz = t59;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t80;
                                            FPy = t49;
                                            FPz = t29;
                                        } else {
                                            FPx = t80;
                                            FPy = t49;
                                            FPz = t59;
                                        }
                                    }
                                } else {
                                    FPx = t80;
                                    FPy = t49;
                                    FPz = t50;
                                }
                            } else {
                                if (t1 == 0.0) {
                                    if (FPz >= 2.0) {
                                        if (t17) {
                                            FPx = t80;
                                            FPy = t39;
                                            FPz = t59;
                                        } else {
                                            if (t16 == 0.0) {
                                                FPx = t80;
                                                FPy = t39;
                                                FPz = t29;
                                            } else {
                                                FPx = t80;
                                                FPy = t39;
                                                FPz = t59;
                                            }
                                        }
                                    } else {
                                        FPx = t80;
                                        FPy = t39;
                                        FPz = t29;
                                    }
                                } else {
                                    if (FPz >= 2.0) {
                                        if (t17) {
                                            FPx = t80;
                                            FPy = t49;
                                            FPz = t59;
                                        } else {
                                            if (t16 == 0.0) {
                                                FPx = t80;
                                                FPy = t49;
                                                FPz = t29;
                                            } else {
                                                FPx = t80;
                                                FPy = t49;
                                                FPz = t59;
                                            }
                                        }
                                    } else {
                                        FPx = t80;
                                        FPy = t49;
                                        FPz = t50;
                                    }
                                }
                            }
                        }
                    } else {
                        if (FPy >= 2.0) {
                            if (t31) {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t74;
                                        FPy = t37;
                                        FPz = t26;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t74;
                                            FPy = t37;
                                            FPz = t29;
                                        } else {
                                            FPx = t74;
                                            FPy = t37;
                                            FPz = t26;
                                        }
                                    }
                                } else {
                                    if (t2) {
                                        FPx = t74;
                                        FPy = t37;
                                        FPz = t15;
                                    } else {
                                        if (t1 == 0.0) {
                                            FPx = t74;
                                            FPy = t37;
                                            FPz = t29;
                                        } else {
                                            FPx = t74;
                                            FPy = t37;
                                            FPz = t15;
                                        }
                                    }
                                }
                            } else {
                                if (t30 == 0.0) {
                                    if (FPz >= 2.0) {
                                        if (t17) {
                                            FPx = t74;
                                            FPy = t39;
                                            FPz = t26;
                                        } else {
                                            if (t16 == 0.0) {
                                                FPx = t74;
                                                FPy = t39;
                                                FPz = t29;
                                            } else {
                                                FPx = t74;
                                                FPy = t39;
                                                FPz = t26;
                                            }
                                        }
                                    } else {
                                        if (t2) {
                                            FPx = t74;
                                            FPy = t39;
                                            FPz = t15;
                                        } else {
                                            if (t1 == 0.0) {
                                                FPx = t74;
                                                FPy = t39;
                                                FPz = t29;
                                            } else {
                                                FPx = t74;
                                                FPy = t39;
                                                FPz = t15;
                                            }
                                        }
                                    }
                                } else {
                                    if (FPz >= 2.0) {
                                        if (t17) {
                                            FPx = t74;
                                            FPy = t37;
                                            FPz = t26;
                                        } else {
                                            if (t16 == 0.0) {
                                                FPx = t74;
                                                FPy = t37;
                                                FPz = t29;
                                            } else {
                                                FPx = t74;
                                                FPy = t37;
                                                FPz = t26;
                                            }
                                        }
                                    } else {
                                        if (t2) {
                                            FPx = t74;
                                            FPy = t37;
                                            FPz = t15;
                                        } else {
                                            if (t1 == 0.0) {
                                                FPx = t74;
                                                FPy = t37;
                                                FPz = t29;
                                            } else {
                                                FPx = t74;
                                                FPy = t37;
                                                FPz = t15;
                                            }
                                        }
                                    }
                                }
                            }
                        } else {
                            if (t2) {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t74;
                                        FPy = t14;
                                        FPz = t26;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t74;
                                            FPy = t14;
                                            FPz = t29;
                                        } else {
                                            FPx = t74;
                                            FPy = t14;
                                            FPz = t26;
                                        }
                                    }
                                } else {
                                    FPx = t74;
                                    FPy = t14;
                                    FPz = t15;
                                }
                            } else {
                                if (t1 == 0.0) {
                                    if (FPz >= 2.0) {
                                        if (t17) {
                                            FPx = t74;
                                            FPy = t39;
                                            FPz = t26;
                                        } else {
                                            if (t16 == 0.0) {
                                                FPx = t74;
                                                FPy = t39;
                                                FPz = t29;
                                            } else {
                                                FPx = t74;
                                                FPy = t39;
                                                FPz = t26;
                                            }
                                        }
                                    } else {
                                        FPx = t74;
                                        FPy = t39;
                                        FPz = t29;
                                    }
                                } else {
                                    if (FPz >= 2.0) {
                                        if (t17) {
                                            FPx = t74;
                                            FPy = t14;
                                            FPz = t26;
                                        } else {
                                            if (t16 == 0.0) {
                                                FPx = t74;
                                                FPy = t14;
                                                FPz = t29;
                                            } else {
                                                FPx = t74;
                                                FPy = t14;
                                                FPz = t26;
                                            }
                                        }
                                    } else {
                                        FPx = t74;
                                        FPy = t14;
                                        FPz = t15;
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    } else {
        if (t2) {
            if (FTy != 0.0) {
                if (FPy >= 2.0) {
                    if (t31) {
                        if (FPz >= 2.0) {
                            if (t17) {
                                FPx = t47;
                                FPy = t65;
                                FPz = t59;
                            } else {
                                if (t16 == 0.0) {
                                    FPx = t47;
                                    FPy = t65;
                                    FPz = t29;
                                } else {
                                    FPx = t47;
                                    FPy = t65;
                                    FPz = t59;
                                }
                            }
                        } else {
                            FPx = t47;
                            FPy = t65;
                            FPz = t50;
                        }
                    } else {
                        if (t30 == 0.0) {
                            if (FPz >= 2.0) {
                                if (t17) {
                                    FPx = t47;
                                    FPy = t39;
                                    FPz = t59;
                                } else {
                                    if (t16 == 0.0) {
                                        FPx = t47;
                                        FPy = t39;
                                        FPz = t29;
                                    } else {
                                        FPx = t47;
                                        FPy = t39;
                                        FPz = t59;
                                    }
                                }
                            } else {
                                FPx = t47;
                                FPy = t39;
                                FPz = t50;
                            }
                        } else {
                            if (FPz >= 2.0) {
                                if (t17) {
                                    FPx = t47;
                                    FPy = t65;
                                    FPz = t59;
                                } else {
                                    if (t16 == 0.0) {
                                        FPx = t47;
                                        FPy = t65;
                                        FPz = t29;
                                    } else {
                                        FPx = t47;
                                        FPy = t65;
                                        FPz = t59;
                                    }
                                }
                            } else {
                                FPx = t47;
                                FPy = t65;
                                FPz = t50;
                            }
                        }
                    }
                } else {
                    if (FPz >= 2.0) {
                        if (t17) {
                            FPx = t47;
                            FPy = t49;
                            FPz = t59;
                        } else {
                            if (t16 == 0.0) {
                                FPx = t47;
                                FPy = t49;
                                FPz = t29;
                            } else {
                                FPx = t47;
                                FPy = t49;
                                FPz = t59;
                            }
                        }
                    } else {
                        FPx = t47;
                        FPy = t49;
                        FPz = t50;
                    }
                }
            } else {
                if (t3) {
                    if (FPy >= 2.0) {
                        if (t31) {
                            if (FPz >= 2.0) {
                                if (t17) {
                                    FPx = t47;
                                    FPy = t65;
                                    FPz = t59;
                                } else {
                                    if (t16 == 0.0) {
                                        FPx = t47;
                                        FPy = t65;
                                        FPz = t29;
                                    } else {
                                        FPx = t47;
                                        FPy = t65;
                                        FPz = t59;
                                    }
                                }
                            } else {
                                FPx = t47;
                                FPy = t65;
                                FPz = t50;
                            }
                        } else {
                            if (t30 == 0.0) {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t47;
                                        FPy = t39;
                                        FPz = t59;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t47;
                                            FPy = t39;
                                            FPz = t29;
                                        } else {
                                            FPx = t47;
                                            FPy = t39;
                                            FPz = t59;
                                        }
                                    }
                                } else {
                                    FPx = t47;
                                    FPy = t39;
                                    FPz = t50;
                                }
                            } else {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t47;
                                        FPy = t65;
                                        FPz = t59;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t47;
                                            FPy = t65;
                                            FPz = t29;
                                        } else {
                                            FPx = t47;
                                            FPy = t65;
                                            FPz = t59;
                                        }
                                    }
                                } else {
                                    FPx = t47;
                                    FPy = t65;
                                    FPz = t50;
                                }
                            }
                        }
                    } else {
                        if (FPz >= 2.0) {
                            if (t17) {
                                FPx = t47;
                                FPy = t49;
                                FPz = t59;
                            } else {
                                if (t16 == 0.0) {
                                    FPx = t47;
                                    FPy = t49;
                                    FPz = t29;
                                } else {
                                    FPx = t47;
                                    FPy = t49;
                                    FPz = t59;
                                }
                            }
                        } else {
                            FPx = t47;
                            FPy = t49;
                            FPz = t50;
                        }
                    }
                } else {
                    if (FPy >= 2.0) {
                        if (t31) {
                            if (FPz >= 2.0) {
                                if (t17) {
                                    FPx = t12;
                                    FPy = t37;
                                    FPz = t26;
                                } else {
                                    if (t16 == 0.0) {
                                        FPx = t12;
                                        FPy = t37;
                                        FPz = t29;
                                    } else {
                                        FPx = t12;
                                        FPy = t37;
                                        FPz = t26;
                                    }
                                }
                            } else {
                                FPx = t12;
                                FPy = t37;
                                FPz = t15;
                            }
                        } else {
                            if (t30 == 0.0) {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t12;
                                        FPy = t39;
                                        FPz = t26;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t12;
                                            FPy = t39;
                                            FPz = t29;
                                        } else {
                                            FPx = t12;
                                            FPy = t39;
                                            FPz = t26;
                                        }
                                    }
                                } else {
                                    FPx = t12;
                                    FPy = t39;
                                    FPz = t15;
                                }
                            } else {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t12;
                                        FPy = t37;
                                        FPz = t26;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t12;
                                            FPy = t37;
                                            FPz = t29;
                                        } else {
                                            FPx = t12;
                                            FPy = t37;
                                            FPz = t26;
                                        }
                                    }
                                } else {
                                    FPx = t12;
                                    FPy = t37;
                                    FPz = t15;
                                }
                            }
                        }
                    } else {
                        if (FPz >= 2.0) {
                            if (t17) {
                                FPx = t12;
                                FPy = t14;
                                FPz = t26;
                            } else {
                                if (t16 == 0.0) {
                                    FPx = t12;
                                    FPy = t14;
                                    FPz = t29;
                                } else {
                                    FPx = t12;
                                    FPy = t14;
                                    FPz = t26;
                                }
                            }
                        } else {
                            FPx = t12;
                            FPy = t14;
                            FPz = t15;
                        }
                    }
                }
            }
        } else {
            if (t1 == 0.0) {
                if (FPy >= 2.0) {
                    if (t31) {
                        if (FTy != 0.0) {
                            if (FPz >= 2.0) {
                                if (t17) {
                                    FPx = t66;
                                    FPy = t65;
                                    FPz = t59;
                                } else {
                                    if (t16 == 0.0) {
                                        FPx = t66;
                                        FPy = t65;
                                        FPz = t29;
                                    } else {
                                        FPx = t66;
                                        FPy = t65;
                                        FPz = t59;
                                    }
                                }
                            } else {
                                FPx = t66;
                                FPy = t65;
                                FPz = t29;
                            }
                        } else {
                            if (t3) {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t66;
                                        FPy = t65;
                                        FPz = t59;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t66;
                                            FPy = t65;
                                            FPz = t29;
                                        } else {
                                            FPx = t66;
                                            FPy = t65;
                                            FPz = t59;
                                        }
                                    }
                                } else {
                                    FPx = t66;
                                    FPy = t65;
                                    FPz = t29;
                                }
                            } else {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t66;
                                        FPy = t37;
                                        FPz = t26;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t66;
                                            FPy = t37;
                                            FPz = t29;
                                        } else {
                                            FPx = t66;
                                            FPy = t37;
                                            FPz = t26;
                                        }
                                    }
                                } else {
                                    FPx = t66;
                                    FPy = t37;
                                    FPz = t29;
                                }
                            }
                        }
                    } else {
                        if (t30 == 0.0) {
                            if (FPz >= 2.0) {
                                if (t17) {
                                    if (FTy != 0.0) {
                                        FPx = t66;
                                        FPy = t39;
                                        FPz = t59;
                                    } else {
                                        if (t3) {
                                            FPx = t66;
                                            FPy = t39;
                                            FPz = t59;
                                        } else {
                                            FPx = t66;
                                            FPy = t39;
                                            FPz = t26;
                                        }
                                    }
                                } else {
                                    if (t16 == 0.0) {
                                        FPx = t66;
                                        FPy = t39;
                                        FPz = t29;
                                    } else {
                                        if (FTy != 0.0) {
                                            FPx = t66;
                                            FPy = t39;
                                            FPz = t59;
                                        } else {
                                            if (t3) {
                                                FPx = t66;
                                                FPy = t39;
                                                FPz = t59;
                                            } else {
                                                FPx = t66;
                                                FPy = t39;
                                                FPz = t26;
                                            }
                                        }
                                    }
                                }
                            } else {
                                FPx = t66;
                                FPy = t39;
                                FPz = t29;
                            }
                        } else {
                            if (FTy != 0.0) {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t66;
                                        FPy = t65;
                                        FPz = t59;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t66;
                                            FPy = t65;
                                            FPz = t29;
                                        } else {
                                            FPx = t66;
                                            FPy = t65;
                                            FPz = t59;
                                        }
                                    }
                                } else {
                                    FPx = t66;
                                    FPy = t65;
                                    FPz = t29;
                                }
                            } else {
                                if (t3) {
                                    if (FPz >= 2.0) {
                                        if (t17) {
                                            FPx = t66;
                                            FPy = t65;
                                            FPz = t59;
                                        } else {
                                            if (t16 == 0.0) {
                                                FPx = t66;
                                                FPy = t65;
                                                FPz = t29;
                                            } else {
                                                FPx = t66;
                                                FPy = t65;
                                                FPz = t59;
                                            }
                                        }
                                    } else {
                                        FPx = t66;
                                        FPy = t65;
                                        FPz = t29;
                                    }
                                } else {
                                    if (FPz >= 2.0) {
                                        if (t17) {
                                            FPx = t66;
                                            FPy = t37;
                                            FPz = t26;
                                        } else {
                                            if (t16 == 0.0) {
                                                FPx = t66;
                                                FPy = t37;
                                                FPz = t29;
                                            } else {
                                                FPx = t66;
                                                FPy = t37;
                                                FPz = t26;
                                            }
                                        }
                                    } else {
                                        FPx = t66;
                                        FPy = t37;
                                        FPz = t29;
                                    }
                                }
                            }
                        }
                    }
                } else {
                    if (FPz >= 2.0) {
                        if (t17) {
                            if (FTy != 0.0) {
                                FPx = t66;
                                FPy = t39;
                                FPz = t59;
                            } else {
                                if (t3) {
                                    FPx = t66;
                                    FPy = t39;
                                    FPz = t59;
                                } else {
                                    FPx = t66;
                                    FPy = t39;
                                    FPz = t26;
                                }
                            }
                        } else {
                            if (t16 == 0.0) {
                                FPx = t66;
                                FPy = t39;
                                FPz = t29;
                            } else {
                                if (FTy != 0.0) {
                                    FPx = t66;
                                    FPy = t39;
                                    FPz = t59;
                                } else {
                                    if (t3) {
                                        FPx = t66;
                                        FPy = t39;
                                        FPz = t59;
                                    } else {
                                        FPx = t66;
                                        FPy = t39;
                                        FPz = t26;
                                    }
                                }
                            }
                        }
                    } else {
                        FPx = t66;
                        FPy = t39;
                        FPz = t29;
                    }
                }
            } else {
                if (FTy != 0.0) {
                    if (FPy >= 2.0) {
                        if (t31) {
                            if (FPz >= 2.0) {
                                if (t17) {
                                    FPx = t47;
                                    FPy = t65;
                                    FPz = t59;
                                } else {
                                    if (t16 == 0.0) {
                                        FPx = t47;
                                        FPy = t65;
                                        FPz = t29;
                                    } else {
                                        FPx = t47;
                                        FPy = t65;
                                        FPz = t59;
                                    }
                                }
                            } else {
                                FPx = t47;
                                FPy = t65;
                                FPz = t50;
                            }
                        } else {
                            if (t30 == 0.0) {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t47;
                                        FPy = t39;
                                        FPz = t59;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t47;
                                            FPy = t39;
                                            FPz = t29;
                                        } else {
                                            FPx = t47;
                                            FPy = t39;
                                            FPz = t59;
                                        }
                                    }
                                } else {
                                    FPx = t47;
                                    FPy = t39;
                                    FPz = t50;
                                }
                            } else {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t47;
                                        FPy = t65;
                                        FPz = t59;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t47;
                                            FPy = t65;
                                            FPz = t29;
                                        } else {
                                            FPx = t47;
                                            FPy = t65;
                                            FPz = t59;
                                        }
                                    }
                                } else {
                                    FPx = t47;
                                    FPy = t65;
                                    FPz = t50;
                                }
                            }
                        }
                    } else {
                        if (FPz >= 2.0) {
                            if (t17) {
                                FPx = t47;
                                FPy = t49;
                                FPz = t59;
                            } else {
                                if (t16 == 0.0) {
                                    FPx = t47;
                                    FPy = t49;
                                    FPz = t29;
                                } else {
                                    FPx = t47;
                                    FPy = t49;
                                    FPz = t59;
                                }
                            }
                        } else {
                            FPx = t47;
                            FPy = t49;
                            FPz = t50;
                        }
                    }
                } else {
                    if (t3) {
                        if (FPy >= 2.0) {
                            if (t31) {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t47;
                                        FPy = t65;
                                        FPz = t59;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t47;
                                            FPy = t65;
                                            FPz = t29;
                                        } else {
                                            FPx = t47;
                                            FPy = t65;
                                            FPz = t59;
                                        }
                                    }
                                } else {
                                    FPx = t47;
                                    FPy = t65;
                                    FPz = t50;
                                }
                            } else {
                                if (t30 == 0.0) {
                                    if (FPz >= 2.0) {
                                        if (t17) {
                                            FPx = t47;
                                            FPy = t39;
                                            FPz = t59;
                                        } else {
                                            if (t16 == 0.0) {
                                                FPx = t47;
                                                FPy = t39;
                                                FPz = t29;
                                            } else {
                                                FPx = t47;
                                                FPy = t39;
                                                FPz = t59;
                                            }
                                        }
                                    } else {
                                        FPx = t47;
                                        FPy = t39;
                                        FPz = t50;
                                    }
                                } else {
                                    if (FPz >= 2.0) {
                                        if (t17) {
                                            FPx = t47;
                                            FPy = t65;
                                            FPz = t59;
                                        } else {
                                            if (t16 == 0.0) {
                                                FPx = t47;
                                                FPy = t65;
                                                FPz = t29;
                                            } else {
                                                FPx = t47;
                                                FPy = t65;
                                                FPz = t59;
                                            }
                                        }
                                    } else {
                                        FPx = t47;
                                        FPy = t65;
                                        FPz = t50;
                                    }
                                }
                            }
                        } else {
                            if (FPz >= 2.0) {
                                if (t17) {
                                    FPx = t47;
                                    FPy = t49;
                                    FPz = t59;
                                } else {
                                    if (t16 == 0.0) {
                                        FPx = t47;
                                        FPy = t49;
                                        FPz = t29;
                                    } else {
                                        FPx = t47;
                                        FPy = t49;
                                        FPz = t59;
                                    }
                                }
                            } else {
                                FPx = t47;
                                FPy = t49;
                                FPz = t50;
                            }
                        }
                    } else {
                        if (FPy >= 2.0) {
                            if (t31) {
                                if (FPz >= 2.0) {
                                    if (t17) {
                                        FPx = t12;
                                        FPy = t37;
                                        FPz = t26;
                                    } else {
                                        if (t16 == 0.0) {
                                            FPx = t12;
                                            FPy = t37;
                                            FPz = t29;
                                        } else {
                                            FPx = t12;
                                            FPy = t37;
                                            FPz = t26;
                                        }
                                    }
                                } else {
                                    FPx = t12;
                                    FPy = t37;
                                    FPz = t15;
                                }
                            } else {
                                if (t30 == 0.0) {
                                    if (FPz >= 2.0) {
                                        if (t17) {
                                            FPx = t12;
                                            FPy = t39;
                                            FPz = t26;
                                        } else {
                                            if (t16 == 0.0) {
                                                FPx = t12;
                                                FPy = t39;
                                                FPz = t29;
                                            } else {
                                                FPx = t12;
                                                FPy = t39;
                                                FPz = t26;
                                            }
                                        }
                                    } else {
                                        FPx = t12;
                                        FPy = t39;
                                        FPz = t15;
                                    }
                                } else {
                                    if (FPz >= 2.0) {
                                        if (t17) {
                                            FPx = t12;
                                            FPy = t37;
                                            FPz = t26;
                                        } else {
                                            if (t16 == 0.0) {
                                                FPx = t12;
                                                FPy = t37;
                                                FPz = t29;
                                            } else {
                                                FPx = t12;
                                                FPy = t37;
                                                FPz = t26;
                                            }
                                        }
                                    } else {
                                        FPx = t12;
                                        FPy = t37;
                                        FPz = t15;
                                    }
                                }
                            }
                        } else {
                            if (FPz >= 2.0) {
                                if (t17) {
                                    FPx = t12;
                                    FPy = t14;
                                    FPz = t26;
                                } else {
                                    if (t16 == 0.0) {
                                        FPx = t12;
                                        FPy = t14;
                                        FPz = t29;
                                    } else {
                                        FPx = t12;
                                        FPy = t14;
                                        FPz = t26;
                                    }
                                }
                            } else {
                                FPx = t12;
                                FPy = t14;
                                FPz = t15;
                            }
                        }
                    }
                }
            }
        }
    }
    return TRUE;
}