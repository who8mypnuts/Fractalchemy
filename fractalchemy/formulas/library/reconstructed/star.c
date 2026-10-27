/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        star.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from star.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    int star_rotate;
    double m_10;
    double m_18;
    double m_20;
    double m_28;
    double m_30;
    double m_38;
    double m_40;
    double m_8;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("star");
APO_VARIABLES(
    VAR_INTEGER(star_rotate, 0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_8) = cos(0.6283185307179586);
    VAR(m_18) = -2.827433388230814;
    VAR(m_20) = -M_PI_2;
    VAR(m_28) = -0.3141592653589793;
    VAR(m_30) = 0.9424777960769379;
    VAR(m_10) = tan(0.6283185307179586);
    VAR(m_38) = 2.199114857512855;
    VAR(m_40) = 1.2566370614359172;
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = atan2(FTy, FTx);
    double t2 = VAR(m_40) + VAR(m_40) + t1;
    double t3 = sqrt(FTy * FTy + FTx * FTx);
    double t4 = sin(t2) * t3;
    double t5 = t1 + VAR(m_40) * (double)VAR(star_rotate);
    double t6 = cos(t5) * t3 + FPx;
    double t7 = t3 * sin(t5) + FPy;
    double t8 = cos(t1);
    double t9 = t8 * t3 + FPx;
    double t10 = sin(t1);
    double t11 = t3 * t10 + FPy;
    double t12 = -VAR(m_40) + t1;
    double t13 = sin(t12) * t3;
    double t14 = -2.0 * VAR(m_40) + t1;
    double t15 = sin(t14) * t3;
    double t16 = t10 * t3;
    double t17 = VAR(m_40) + t1;
    double t18 = sin(t17) * t3;
    if (VAR(m_18) >= t1) {
        if (!(VAR(m_20) >= t1)) {
            if (!(VAR(m_28) > t1)) {
                if (VAR(m_30) >= t1) {
                    if (!(VAR(m_38) >= t1)) {
                        if (!(VAR(m_8) >= t15)) {
                            FPx = t9;
                            FPy = t11;
                        } else {
                            if (t3 * cos(t14) * VAR(m_10) - 1.0 > t15) {
                                FPx = t9;
                                FPy = t11;
                            } else {
                                FPx = t6;
                                FPy = t7;
                            }
                        }
                    } else {
                        if (!(VAR(m_18) > t1)) {
                            if (!(VAR(m_8) >= t16)) {
                                FPx = t9;
                                FPy = t11;
                            } else {
                                if (t3 * t8 * VAR(m_10) - 1.0 > t16) {
                                    FPx = t9;
                                    FPy = t11;
                                } else {
                                    FPx = t6;
                                    FPy = t7;
                                }
                            }
                        } else {
                            if (!(VAR(m_8) >= t15)) {
                                FPx = t9;
                                FPy = t11;
                            } else {
                                if (t3 * cos(t14) * VAR(m_10) - 1.0 > t15) {
                                    FPx = t9;
                                    FPy = t11;
                                } else {
                                    FPx = t6;
                                    FPy = t7;
                                }
                            }
                        }
                    }
                } else {
                    if (!(VAR(m_38) > t1)) {
                        if (!(VAR(m_38) >= t1)) {
                            if (!(VAR(m_8) >= t15)) {
                                FPx = t9;
                                FPy = t11;
                            } else {
                                if (t3 * cos(t14) * VAR(m_10) - 1.0 > t15) {
                                    FPx = t9;
                                    FPy = t11;
                                } else {
                                    FPx = t6;
                                    FPy = t7;
                                }
                            }
                        } else {
                            if (!(VAR(m_18) > t1)) {
                                if (!(VAR(m_8) >= t16)) {
                                    FPx = t9;
                                    FPy = t11;
                                } else {
                                    if (t3 * t8 * VAR(m_10) - 1.0 > t16) {
                                        FPx = t9;
                                        FPy = t11;
                                    } else {
                                        FPx = t6;
                                        FPy = t7;
                                    }
                                }
                            } else {
                                if (!(VAR(m_8) >= t15)) {
                                    FPx = t9;
                                    FPy = t11;
                                } else {
                                    if (t3 * cos(t14) * VAR(m_10) - 1.0 > t15) {
                                        FPx = t9;
                                        FPy = t11;
                                    } else {
                                        FPx = t6;
                                        FPy = t7;
                                    }
                                }
                            }
                        }
                    } else {
                        if (!(VAR(m_8) >= t13)) {
                            FPx = t9;
                            FPy = t11;
                        } else {
                            if (t3 * cos(t12) * VAR(m_10) - 1.0 > t13) {
                                FPx = t9;
                                FPy = t11;
                            } else {
                                FPx = t6;
                                FPy = t7;
                            }
                        }
                    }
                }
            } else {
                if (!(VAR(m_8) >= t18)) {
                    FPx = t9;
                    FPy = t11;
                } else {
                    if (t3 * cos(t17) * VAR(m_10) - 1.0 > t18) {
                        FPx = t9;
                        FPy = t11;
                    } else {
                        FPx = t6;
                        FPy = t7;
                    }
                }
            }
        } else {
            if (VAR(m_30) >= t1) {
                if (!(VAR(m_38) >= t1)) {
                    if (!(VAR(m_8) >= t15)) {
                        FPx = t9;
                        FPy = t11;
                    } else {
                        if (t3 * cos(t14) * VAR(m_10) - 1.0 > t15) {
                            FPx = t9;
                            FPy = t11;
                        } else {
                            FPx = t6;
                            FPy = t7;
                        }
                    }
                } else {
                    if (!(VAR(m_18) > t1)) {
                        if (!(VAR(m_8) >= t16)) {
                            FPx = t9;
                            FPy = t11;
                        } else {
                            if (t3 * t8 * VAR(m_10) - 1.0 > t16) {
                                FPx = t9;
                                FPy = t11;
                            } else {
                                FPx = t6;
                                FPy = t7;
                            }
                        }
                    } else {
                        if (!(VAR(m_8) >= t15)) {
                            FPx = t9;
                            FPy = t11;
                        } else {
                            if (t3 * cos(t14) * VAR(m_10) - 1.0 > t15) {
                                FPx = t9;
                                FPy = t11;
                            } else {
                                FPx = t6;
                                FPy = t7;
                            }
                        }
                    }
                }
            } else {
                if (!(VAR(m_38) > t1)) {
                    if (!(VAR(m_38) >= t1)) {
                        if (!(VAR(m_8) >= t15)) {
                            FPx = t9;
                            FPy = t11;
                        } else {
                            if (t3 * cos(t14) * VAR(m_10) - 1.0 > t15) {
                                FPx = t9;
                                FPy = t11;
                            } else {
                                FPx = t6;
                                FPy = t7;
                            }
                        }
                    } else {
                        if (!(VAR(m_18) > t1)) {
                            if (!(VAR(m_8) >= t16)) {
                                FPx = t9;
                                FPy = t11;
                            } else {
                                if (t3 * t8 * VAR(m_10) - 1.0 > t16) {
                                    FPx = t9;
                                    FPy = t11;
                                } else {
                                    FPx = t6;
                                    FPy = t7;
                                }
                            }
                        } else {
                            if (!(VAR(m_8) >= t15)) {
                                FPx = t9;
                                FPy = t11;
                            } else {
                                if (t3 * cos(t14) * VAR(m_10) - 1.0 > t15) {
                                    FPx = t9;
                                    FPy = t11;
                                } else {
                                    FPx = t6;
                                    FPy = t7;
                                }
                            }
                        }
                    }
                } else {
                    if (!(VAR(m_8) >= t13)) {
                        FPx = t9;
                        FPy = t11;
                    } else {
                        if (t3 * cos(t12) * VAR(m_10) - 1.0 > t13) {
                            FPx = t9;
                            FPy = t11;
                        } else {
                            FPx = t6;
                            FPy = t7;
                        }
                    }
                }
            }
        }
    } else {
        if (!(VAR(m_20) > t1)) {
            if (!(VAR(m_20) >= t1)) {
                if (!(VAR(m_28) > t1)) {
                    if (VAR(m_30) >= t1) {
                        if (!(VAR(m_38) >= t1)) {
                            if (!(VAR(m_8) >= t15)) {
                                FPx = t9;
                                FPy = t11;
                            } else {
                                if (t3 * cos(t14) * VAR(m_10) - 1.0 > t15) {
                                    FPx = t9;
                                    FPy = t11;
                                } else {
                                    FPx = t6;
                                    FPy = t7;
                                }
                            }
                        } else {
                            if (!(VAR(m_18) > t1)) {
                                if (!(VAR(m_8) >= t16)) {
                                    FPx = t9;
                                    FPy = t11;
                                } else {
                                    if (t3 * t8 * VAR(m_10) - 1.0 > t16) {
                                        FPx = t9;
                                        FPy = t11;
                                    } else {
                                        FPx = t6;
                                        FPy = t7;
                                    }
                                }
                            } else {
                                if (!(VAR(m_8) >= t15)) {
                                    FPx = t9;
                                    FPy = t11;
                                } else {
                                    if (t3 * cos(t14) * VAR(m_10) - 1.0 > t15) {
                                        FPx = t9;
                                        FPy = t11;
                                    } else {
                                        FPx = t6;
                                        FPy = t7;
                                    }
                                }
                            }
                        }
                    } else {
                        if (!(VAR(m_38) > t1)) {
                            if (!(VAR(m_38) >= t1)) {
                                if (!(VAR(m_8) >= t15)) {
                                    FPx = t9;
                                    FPy = t11;
                                } else {
                                    if (t3 * cos(t14) * VAR(m_10) - 1.0 > t15) {
                                        FPx = t9;
                                        FPy = t11;
                                    } else {
                                        FPx = t6;
                                        FPy = t7;
                                    }
                                }
                            } else {
                                if (!(VAR(m_18) > t1)) {
                                    if (!(VAR(m_8) >= t16)) {
                                        FPx = t9;
                                        FPy = t11;
                                    } else {
                                        if (t3 * t8 * VAR(m_10) - 1.0 > t16) {
                                            FPx = t9;
                                            FPy = t11;
                                        } else {
                                            FPx = t6;
                                            FPy = t7;
                                        }
                                    }
                                } else {
                                    if (!(VAR(m_8) >= t15)) {
                                        FPx = t9;
                                        FPy = t11;
                                    } else {
                                        if (t3 * cos(t14) * VAR(m_10) - 1.0 > t15) {
                                            FPx = t9;
                                            FPy = t11;
                                        } else {
                                            FPx = t6;
                                            FPy = t7;
                                        }
                                    }
                                }
                            }
                        } else {
                            if (!(VAR(m_8) >= t13)) {
                                FPx = t9;
                                FPy = t11;
                            } else {
                                if (t3 * cos(t12) * VAR(m_10) - 1.0 > t13) {
                                    FPx = t9;
                                    FPy = t11;
                                } else {
                                    FPx = t6;
                                    FPy = t7;
                                }
                            }
                        }
                    }
                } else {
                    if (!(VAR(m_8) >= t18)) {
                        FPx = t9;
                        FPy = t11;
                    } else {
                        if (t3 * cos(t17) * VAR(m_10) - 1.0 > t18) {
                            FPx = t9;
                            FPy = t11;
                        } else {
                            FPx = t6;
                            FPy = t7;
                        }
                    }
                }
            } else {
                if (VAR(m_30) >= t1) {
                    if (!(VAR(m_38) >= t1)) {
                        if (!(VAR(m_8) >= t15)) {
                            FPx = t9;
                            FPy = t11;
                        } else {
                            if (t3 * cos(t14) * VAR(m_10) - 1.0 > t15) {
                                FPx = t9;
                                FPy = t11;
                            } else {
                                FPx = t6;
                                FPy = t7;
                            }
                        }
                    } else {
                        if (!(VAR(m_18) > t1)) {
                            if (!(VAR(m_8) >= t16)) {
                                FPx = t9;
                                FPy = t11;
                            } else {
                                if (t3 * t8 * VAR(m_10) - 1.0 > t16) {
                                    FPx = t9;
                                    FPy = t11;
                                } else {
                                    FPx = t6;
                                    FPy = t7;
                                }
                            }
                        } else {
                            if (!(VAR(m_8) >= t15)) {
                                FPx = t9;
                                FPy = t11;
                            } else {
                                if (t3 * cos(t14) * VAR(m_10) - 1.0 > t15) {
                                    FPx = t9;
                                    FPy = t11;
                                } else {
                                    FPx = t6;
                                    FPy = t7;
                                }
                            }
                        }
                    }
                } else {
                    if (!(VAR(m_38) > t1)) {
                        if (!(VAR(m_38) >= t1)) {
                            if (!(VAR(m_8) >= t15)) {
                                FPx = t9;
                                FPy = t11;
                            } else {
                                if (t3 * cos(t14) * VAR(m_10) - 1.0 > t15) {
                                    FPx = t9;
                                    FPy = t11;
                                } else {
                                    FPx = t6;
                                    FPy = t7;
                                }
                            }
                        } else {
                            if (!(VAR(m_18) > t1)) {
                                if (!(VAR(m_8) >= t16)) {
                                    FPx = t9;
                                    FPy = t11;
                                } else {
                                    if (t3 * t8 * VAR(m_10) - 1.0 > t16) {
                                        FPx = t9;
                                        FPy = t11;
                                    } else {
                                        FPx = t6;
                                        FPy = t7;
                                    }
                                }
                            } else {
                                if (!(VAR(m_8) >= t15)) {
                                    FPx = t9;
                                    FPy = t11;
                                } else {
                                    if (t3 * cos(t14) * VAR(m_10) - 1.0 > t15) {
                                        FPx = t9;
                                        FPy = t11;
                                    } else {
                                        FPx = t6;
                                        FPy = t7;
                                    }
                                }
                            }
                        }
                    } else {
                        if (!(VAR(m_8) >= t13)) {
                            FPx = t9;
                            FPy = t11;
                        } else {
                            if (t3 * cos(t12) * VAR(m_10) - 1.0 > t13) {
                                FPx = t9;
                                FPy = t11;
                            } else {
                                FPx = t6;
                                FPy = t7;
                            }
                        }
                    }
                }
            }
        } else {
            if (!(VAR(m_8) >= t4)) {
                FPx = t9;
                FPy = t11;
            } else {
                if (t3 * cos(t2) * VAR(m_10) - 1.0 > t4) {
                    FPx = t9;
                    FPy = t11;
                } else {
                    FPx = t6;
                    FPy = t7;
                }
            }
        }
    }
    return TRUE;
}