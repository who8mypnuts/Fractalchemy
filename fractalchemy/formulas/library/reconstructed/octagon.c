/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        octagon.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from octagon.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double octa_x;
    double octa_y;
    double octa_z;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("octagon");
APO_VARIABLES(
    VAR_REAL(octa_x, 0.0),
    VAR_REAL(octa_y, 0.0),
    VAR_REAL(octa_z, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTz * FTz;
    double t2 = FTy * FTy;
    double t3 = FTx * FTx;
    double t4 = VVAR / (t1 + (t2 * t2 + (t1 + t3 * t3)) + 1e-20);
    double t5 = VVAR * FTx;
    double t6 = t5 + FPx;
    double t7 = VVAR * FTy;
    double t8 = t7 + FPy;
    double t9 = VVAR * FTz;
    double t10 = t9 + FPz;
    double t11 = t5 + t6;
    double t12 = t7 + t8;
    double t13 = t9 + t10;
    double t14 = (FTx - VAR(octa_x)) * VVAR;
    double t15 = t14 + t11;
    double t16 = (FTy - VAR(octa_y)) * VVAR;
    double t17 = t16 + t12;
    double t18 = (FTz - VAR(octa_z)) * VVAR;
    double t19 = t18 + t13;
    double t20 = (FTz + VAR(octa_z)) * VVAR;
    double t21 = t20 + t13;
    double t22 = (FTy + VAR(octa_y)) * VVAR;
    double t23 = t22 + t12;
    double t24 = (FTx + VAR(octa_x)) * VVAR;
    double t25 = t24 + t11;
    double t26 = sqrt(FTz);
    double t27 = VVAR / (t26 + (fabs(FTy) + (t26 + fabs(FTx))) + 1e-20);
    double t28 = FTx * t27 + t6;
    double t29 = FTy * t27 + t8;
    double t30 = FTz * t27 + t10;
    double t31 = t14 + t28;
    double t32 = t16 + t29;
    double t33 = t18 + t30;
    double t34 = t20 + t30;
    double t35 = t22 + t29;
    double t36 = t24 + t28;
    if (2.0 > t4) {
        FPx = FTx * t4 + FPx;
        FPy = FTy * t4 + FPy;
        FPz = FTz * t4 + FPz;
    } else {
        if (t4 >= 0.0) {
            if (FTx >= 0.0) {
                if (FTy >= 0.0) {
                    if (FTz >= 0.0) {
                        FPx = t36;
                        FPy = t35;
                        FPz = t34;
                    } else {
                        FPx = t36;
                        FPy = t35;
                        FPz = t33;
                    }
                } else {
                    if (FTz >= 0.0) {
                        FPx = t36;
                        FPy = t32;
                        FPz = t34;
                    } else {
                        FPx = t36;
                        FPy = t32;
                        FPz = t33;
                    }
                }
            } else {
                if (FTy >= 0.0) {
                    if (FTz >= 0.0) {
                        FPx = t31;
                        FPy = t35;
                        FPz = t34;
                    } else {
                        FPx = t31;
                        FPy = t35;
                        FPz = t33;
                    }
                } else {
                    if (FTz >= 0.0) {
                        FPx = t31;
                        FPy = t32;
                        FPz = t34;
                    } else {
                        FPx = t31;
                        FPy = t32;
                        FPz = t33;
                    }
                }
            }
        } else {
            if (FTx >= 0.0) {
                if (FTy >= 0.0) {
                    if (FTz >= 0.0) {
                        FPx = t25;
                        FPy = t23;
                        FPz = t21;
                    } else {
                        FPx = t25;
                        FPy = t23;
                        FPz = t19;
                    }
                } else {
                    if (FTz >= 0.0) {
                        FPx = t25;
                        FPy = t17;
                        FPz = t21;
                    } else {
                        FPx = t25;
                        FPy = t17;
                        FPz = t19;
                    }
                }
            } else {
                if (FTy >= 0.0) {
                    if (FTz >= 0.0) {
                        FPx = t15;
                        FPy = t23;
                        FPz = t21;
                    } else {
                        FPx = t15;
                        FPy = t23;
                        FPz = t19;
                    }
                } else {
                    if (FTz >= 0.0) {
                        FPx = t15;
                        FPy = t17;
                        FPz = t21;
                    } else {
                        FPx = t15;
                        FPy = t17;
                        FPz = t19;
                    }
                }
            }
        }
    }
    return TRUE;
}