/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        triangle.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from triangle.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz', 32: 'TC'} var_base=88

typedef struct {

} Variables;
#include "apoplugin.h"
APO_PLUGIN("triangle");
APO_VARIABLES(

);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = 0.0 * TM(b);
    double t2 = TM(a) + t1 + TM(e);
    double t3 = 0.0 * TM(a);
    double t4 = t3 + t1 + TM(e);
    double t5 = t2 - t4;
    double t6 = 0.0 * TM(d);
    double t7 = TM(c) * t4 + t6 + TM(f);
    double t8 = TM(c) * t2 + t6 + TM(f) - t7;
    double t9 = t5 * t5 + t8 * t8;
    double t10 = (t3 - TM(b)) + TM(e);
    double t11 = t10 - t4;
    double t12 = FTx - t4;
    double t13 = (TM(c) * t10 - TM(d)) + TM(f) - t7;
    double t14 = FTy - t7;
    double t15 = t11 * t12 + t13 * t14;
    double t16 = t11 * t5 + t13 * t8;
    double t17 = t5 * t12 + t5 * t14;
    double t18 = t11 * t11 + t13 * t13;
    double t19 = 1.0 / (t18 * t9 - t16 * t16);
    double t20 = (t9 * t15 - t16 * t17) * t19;
    double t21 = 0.0 * VVAR;
    double t22 = t21 + FPx;
    double t23 = t21 + FPy;
    double t24 = VVAR * FTz + FPz;
    double t25 = VVAR * FTx + FPx;
    double t26 = VVAR * FTy + FPy;
    double t27 = (t18 * t17 - t16 * t15) * t19;
    if (t20 > 0.0) {
        if (t27 > 0.0) {
            if (1.0 > t20 + t27) {
                if (1 != 0) {
                    FPx = t25;
                    FPy = t26;
                    FPz = t24;
                } else {
                    FPx = t22;
                    FPy = t23;
                    FPz = t24;
                }
            } else {
                if (0 != 0) {
                    FPx = t25;
                    FPy = t26;
                    FPz = t24;
                } else {
                    FPx = t22;
                    FPy = t23;
                    FPz = t24;
                }
            }
        } else {
            if (0 != 0) {
                FPx = t25;
                FPy = t26;
                FPz = t24;
            } else {
                FPx = t22;
                FPy = t23;
                FPz = t24;
            }
        }
    } else {
        if (0 != 0) {
            FPx = t25;
            FPy = t26;
            FPz = t24;
        } else {
            FPx = t22;
            FPy = t23;
            FPz = t24;
        }
    }
    return TRUE;
}