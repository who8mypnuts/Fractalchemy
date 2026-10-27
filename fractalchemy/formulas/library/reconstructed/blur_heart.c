/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        blur_heart.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from blur_heart.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    int blur_heart_p;
    int blur_heart_a;
    int blur_heart_b;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("blur_heart");
APO_VARIABLES(
    VAR_INTEGER(blur_heart_p, 0),
    VAR_INTEGER(blur_heart_a, 858993459),
    VAR_INTEGER(blur_heart_b, 1717986918)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = random01() - 0.5;
    double t2 = t1 + t1;
    double t3 = random01() - 0.5;
    double t4 = t3 + t3;
    double t5 = sqrt(fabs(1.0 - t4 * t4));
    double t6 = pow(fabs(t4), VAR(blur_heart_p)) * VAR(blur_heart_a);
    double t7 = fabs(VAR(blur_heart_b)) + fabs(VAR(blur_heart_a));
    double t8 = (-VAR(blur_heart_b) * t5 + t6 - VAR(blur_heart_a)) / t7;
    double t9 = t4 * VVAR + FPx;
    double t10 = t8 * VVAR + FPy;
    double t11 = t2 * VVAR + FPy;
    double t12 = (VAR(blur_heart_b) * t5 + t6 - VAR(blur_heart_a)) / t7;
    double t13 = t12 * VVAR + FPy;
    if (0.0 <= t2) {
        if (1.0 <= 0.0) {
            if (t12 <= t2) {
                FPx = t9;
                FPy = t11;
            } else {
                FPx = t9;
                FPy = t13;
            }
        } else {
            if (t2 <= t12) {
                FPx = t9;
                FPy = t11;
            } else {
                FPx = t9;
                FPy = t13;
            }
        }
    } else {
        if (-1.0 <= 0.0) {
            if (t8 <= t2) {
                FPx = t9;
                FPy = t11;
            } else {
                FPx = t9;
                FPy = t10;
            }
        } else {
            if (t2 <= t8) {
                FPx = t9;
                FPy = t11;
            } else {
                FPx = t9;
                FPy = t10;
            }
        }
    }
    return TRUE;
}