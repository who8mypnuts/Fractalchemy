/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        StretchyPants.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from StretchyPants.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {

} Variables;
#include "apoplugin.h"
APO_PLUGIN("stretchy_pants");
APO_VARIABLES(

);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = atan2(FTy, FTx);
    double t2 = cos(t1);
    double t3 = 1.0 / t2;
    double t4 = sqrt(FTy * FTy + FTx * FTx);
    double t5 = t3 * t4;
    double t6 = sin(t1);
    double t7 = -t3 * t4;
    double t8 = t2 * (VVAR * t7) + FPx;
    double t9 = t6 * (t7 * VVAR) + FPy;
    double t10 = 1.0 / t6;
    double t11 = -t10 * t4;
    double t12 = t2 * (VVAR * t11) + FPx;
    double t13 = t6 * (t11 * VVAR) + FPy;
    double t14 = t10 * t4;
    double t15 = t2 * (VVAR * t14) + FPx;
    double t16 = t6 * (t14 * VVAR) + FPy;
    if (t1 >= M_PI_4) {
        if (t1 > M_PI_4) {
            if (t1 >= 2.356194490192345) {
                if (t1 >= -M_PI_4) {
                    FPx = t8;
                    FPy = t9;
                } else {
                    if (t1 > -2.356194490192345) {
                        FPx = t12;
                        FPy = t13;
                    } else {
                        FPx = t8;
                        FPy = t9;
                    }
                }
            } else {
                FPx = t15;
                FPy = t16;
            }
        } else {
            if (t1 >= -M_PI_4) {
                FPx = t8;
                FPy = t9;
            } else {
                if (t1 > -2.356194490192345) {
                    FPx = t12;
                    FPy = t13;
                } else {
                    FPx = t8;
                    FPy = t9;
                }
            }
        }
    } else {
        if (!(t1 > -M_PI_4)) {
            if (t1 > M_PI_4) {
                if (t1 >= 2.356194490192345) {
                    if (t1 >= -M_PI_4) {
                        FPx = t8;
                        FPy = t9;
                    } else {
                        if (t1 > -2.356194490192345) {
                            FPx = t12;
                            FPy = t13;
                        } else {
                            FPx = t8;
                            FPy = t9;
                        }
                    }
                } else {
                    FPx = t15;
                    FPy = t16;
                }
            } else {
                if (t1 >= -M_PI_4) {
                    FPx = t8;
                    FPy = t9;
                } else {
                    if (t1 > -2.356194490192345) {
                        FPx = t12;
                        FPy = t13;
                    } else {
                        FPx = t8;
                        FPy = t9;
                    }
                }
            }
        } else {
            FPx = t2 * (VVAR * t5) + FPx;
            FPy = t6 * (t5 * VVAR) + FPy;
        }
    }
    return TRUE;
}