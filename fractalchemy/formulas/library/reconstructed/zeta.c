/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        zeta.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from zeta.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {

} Variables;
#include "apoplugin.h"
APO_PLUGIN("zeta");
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
    double t11 = ((t8 + 0.0 * t9) / t10) * VVAR + FPx;
    double t12 = ((0.0 * t8 - t9) / t10) * VVAR + FPy;
    double t13 = hypot(FPy, 0.0);
    double t14 = isnan(t13);
    double t15 = atan2(0.0, FPy);
    double t16 = t4 * t15;
    double t17 = pow(t13, t4);
    double t18 = cos(t16) * t17;
    double t19 = sin(t16) * t17;
    double t20 = ((0.0 * t18 - t19) / (t18 * t18 + t19 * t19)) * VVAR + FPy;
    double t21 = (0.0 / 0.0) * VVAR;
    double t22 = t21 + FPy;
    double t23 = log(t1);
    double t24 = FTy * t23 + t6;
    double t25 = exp(t23 * t4 - FTy * t5);
    double t26 = cos(t24) * t25;
    double t27 = sin(t24) * t25;
    double t28 = t26 * t26 + t27 * t27;
    double t29 = ((t26 + 0.0 * t27) / t28) * VVAR + FPx;
    double t30 = ((0.0 * t26 - t27) / t28) * VVAR + FPy;
    double t31 = log(t13);
    double t32 = FTy * t31 + t16;
    double t33 = exp(t31 * t4 - FTy * t15);
    double t34 = cos(t32) * t33;
    double t35 = sin(t32) * t33;
    double t36 = ((0.0 * t34 - t35) / (t34 * t34 + t35 * t35)) * VVAR + FPy;
    double t37 = t21 + FPx;
    double t38 = hypot(FPx, 0.0);
    double t39 = isnan(t38);
    double t40 = atan2(0.0, FPx);
    double t41 = t4 * t40;
    double t42 = pow(t38, t4);
    double t43 = cos(t41) * t42;
    double t44 = sin(t41) * t42;
    double t45 = ((t43 + 0.0 * t44) / (t43 * t43 + t44 * t44)) * VVAR + FPx;
    double t46 = log(t38);
    double t47 = FTy * t46 + t41;
    double t48 = exp(t46 * t4 - FTy * t40);
    double t49 = cos(t47) * t48;
    double t50 = sin(t47) * t48;
    double t51 = ((t49 + 0.0 * t50) / (t49 * t49 + t50 * t50)) * VVAR + FPx;
    if (FPx >= 2.0) {
        if (t39) {
            if (FTy != 0.0) {
                if (FPy >= 2.0) {
                    if (t14) {
                        FPx = t51;
                        FPy = t36;
                    } else {
                        if (t13 == 0.0) {
                            FPx = t51;
                            FPy = t22;
                        } else {
                            FPx = t51;
                            FPy = t36;
                        }
                    }
                } else {
                    if (t2) {
                        FPx = t51;
                        FPy = t30;
                    } else {
                        if (t1 == 0.0) {
                            FPx = t51;
                            FPy = t22;
                        } else {
                            FPx = t51;
                            FPy = t30;
                        }
                    }
                }
            } else {
                if (t3) {
                    if (FPy >= 2.0) {
                        if (t14) {
                            FPx = t51;
                            FPy = t36;
                        } else {
                            if (t13 == 0.0) {
                                FPx = t51;
                                FPy = t22;
                            } else {
                                FPx = t51;
                                FPy = t36;
                            }
                        }
                    } else {
                        if (t2) {
                            FPx = t51;
                            FPy = t30;
                        } else {
                            if (t1 == 0.0) {
                                FPx = t51;
                                FPy = t22;
                            } else {
                                FPx = t51;
                                FPy = t30;
                            }
                        }
                    }
                } else {
                    if (FPy >= 2.0) {
                        if (t14) {
                            FPx = t45;
                            FPy = t20;
                        } else {
                            if (t13 == 0.0) {
                                FPx = t45;
                                FPy = t22;
                            } else {
                                FPx = t45;
                                FPy = t20;
                            }
                        }
                    } else {
                        if (t2) {
                            FPx = t45;
                            FPy = t12;
                        } else {
                            if (t1 == 0.0) {
                                FPx = t45;
                                FPy = t22;
                            } else {
                                FPx = t45;
                                FPy = t12;
                            }
                        }
                    }
                }
            }
        } else {
            if (t38 == 0.0) {
                if (FPy >= 2.0) {
                    if (t14) {
                        if (FTy != 0.0) {
                            FPx = t37;
                            FPy = t36;
                        } else {
                            if (t3) {
                                FPx = t37;
                                FPy = t36;
                            } else {
                                FPx = t37;
                                FPy = t20;
                            }
                        }
                    } else {
                        if (t13 == 0.0) {
                            FPx = t37;
                            FPy = t22;
                        } else {
                            if (FTy != 0.0) {
                                FPx = t37;
                                FPy = t36;
                            } else {
                                if (t3) {
                                    FPx = t37;
                                    FPy = t36;
                                } else {
                                    FPx = t37;
                                    FPy = t20;
                                }
                            }
                        }
                    }
                } else {
                    if (t2) {
                        if (FTy != 0.0) {
                            FPx = t37;
                            FPy = t30;
                        } else {
                            if (t3) {
                                FPx = t37;
                                FPy = t30;
                            } else {
                                FPx = t37;
                                FPy = t12;
                            }
                        }
                    } else {
                        if (t1 == 0.0) {
                            FPx = t37;
                            FPy = t22;
                        } else {
                            if (FTy != 0.0) {
                                FPx = t37;
                                FPy = t30;
                            } else {
                                if (t3) {
                                    FPx = t37;
                                    FPy = t30;
                                } else {
                                    FPx = t37;
                                    FPy = t12;
                                }
                            }
                        }
                    }
                }
            } else {
                if (FTy != 0.0) {
                    if (FPy >= 2.0) {
                        if (t14) {
                            FPx = t51;
                            FPy = t36;
                        } else {
                            if (t13 == 0.0) {
                                FPx = t51;
                                FPy = t22;
                            } else {
                                FPx = t51;
                                FPy = t36;
                            }
                        }
                    } else {
                        if (t2) {
                            FPx = t51;
                            FPy = t30;
                        } else {
                            if (t1 == 0.0) {
                                FPx = t51;
                                FPy = t22;
                            } else {
                                FPx = t51;
                                FPy = t30;
                            }
                        }
                    }
                } else {
                    if (t3) {
                        if (FPy >= 2.0) {
                            if (t14) {
                                FPx = t51;
                                FPy = t36;
                            } else {
                                if (t13 == 0.0) {
                                    FPx = t51;
                                    FPy = t22;
                                } else {
                                    FPx = t51;
                                    FPy = t36;
                                }
                            }
                        } else {
                            if (t2) {
                                FPx = t51;
                                FPy = t30;
                            } else {
                                if (t1 == 0.0) {
                                    FPx = t51;
                                    FPy = t22;
                                } else {
                                    FPx = t51;
                                    FPy = t30;
                                }
                            }
                        }
                    } else {
                        if (FPy >= 2.0) {
                            if (t14) {
                                FPx = t45;
                                FPy = t20;
                            } else {
                                if (t13 == 0.0) {
                                    FPx = t45;
                                    FPy = t22;
                                } else {
                                    FPx = t45;
                                    FPy = t20;
                                }
                            }
                        } else {
                            if (t2) {
                                FPx = t45;
                                FPy = t12;
                            } else {
                                if (t1 == 0.0) {
                                    FPx = t45;
                                    FPy = t22;
                                } else {
                                    FPx = t45;
                                    FPy = t12;
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
                    if (t14) {
                        FPx = t29;
                        FPy = t36;
                    } else {
                        if (t13 == 0.0) {
                            FPx = t29;
                            FPy = t22;
                        } else {
                            FPx = t29;
                            FPy = t36;
                        }
                    }
                } else {
                    FPx = t29;
                    FPy = t30;
                }
            } else {
                if (t3) {
                    if (FPy >= 2.0) {
                        if (t14) {
                            FPx = t29;
                            FPy = t36;
                        } else {
                            if (t13 == 0.0) {
                                FPx = t29;
                                FPy = t22;
                            } else {
                                FPx = t29;
                                FPy = t36;
                            }
                        }
                    } else {
                        FPx = t29;
                        FPy = t30;
                    }
                } else {
                    if (FPy >= 2.0) {
                        if (t14) {
                            FPx = t11;
                            FPy = t20;
                        } else {
                            if (t13 == 0.0) {
                                FPx = t11;
                                FPy = t22;
                            } else {
                                FPx = t11;
                                FPy = t20;
                            }
                        }
                    } else {
                        FPx = t11;
                        FPy = t12;
                    }
                }
            }
        } else {
            if (t1 == 0.0) {
                if (FPy >= 2.0) {
                    if (t14) {
                        if (FTy != 0.0) {
                            FPx = t37;
                            FPy = t36;
                        } else {
                            if (t3) {
                                FPx = t37;
                                FPy = t36;
                            } else {
                                FPx = t37;
                                FPy = t20;
                            }
                        }
                    } else {
                        if (t13 == 0.0) {
                            FPx = t37;
                            FPy = t22;
                        } else {
                            if (FTy != 0.0) {
                                FPx = t37;
                                FPy = t36;
                            } else {
                                if (t3) {
                                    FPx = t37;
                                    FPy = t36;
                                } else {
                                    FPx = t37;
                                    FPy = t20;
                                }
                            }
                        }
                    }
                } else {
                    FPx = t37;
                    FPy = t22;
                }
            } else {
                if (FTy != 0.0) {
                    if (FPy >= 2.0) {
                        if (t14) {
                            FPx = t29;
                            FPy = t36;
                        } else {
                            if (t13 == 0.0) {
                                FPx = t29;
                                FPy = t22;
                            } else {
                                FPx = t29;
                                FPy = t36;
                            }
                        }
                    } else {
                        FPx = t29;
                        FPy = t30;
                    }
                } else {
                    if (t3) {
                        if (FPy >= 2.0) {
                            if (t14) {
                                FPx = t29;
                                FPy = t36;
                            } else {
                                if (t13 == 0.0) {
                                    FPx = t29;
                                    FPy = t22;
                                } else {
                                    FPx = t29;
                                    FPy = t36;
                                }
                            }
                        } else {
                            FPx = t29;
                            FPy = t30;
                        }
                    } else {
                        if (FPy >= 2.0) {
                            if (t14) {
                                FPx = t11;
                                FPy = t20;
                            } else {
                                if (t13 == 0.0) {
                                    FPx = t11;
                                    FPy = t22;
                                } else {
                                    FPx = t11;
                                    FPy = t20;
                                }
                            }
                        } else {
                            FPx = t11;
                            FPy = t12;
                        }
                    }
                }
            }
        }
    }
    return TRUE;
}