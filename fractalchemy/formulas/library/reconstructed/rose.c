/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        rose.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from rose.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz', 32: 'TC'} var_base=88

typedef struct {
    double rose_numer;
    double rose_denom;
    double rose_inner_scale;
    double rose_outer_scale;
    double rose_angle_in;
    double rose_shear_x;
    double rose_shear_y;
    double rose_turn_x;
    double rose_turn_y;
    double rose_strength;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("rose");
APO_VARIABLES(
    VAR_REAL(rose_numer, 2.0),
    VAR_REAL(rose_denom, 1.0),
    VAR_REAL(rose_inner_scale, 1.0),
    VAR_REAL(rose_outer_scale, 1.0),
    VAR_REAL(rose_angle_in, 0.0),
    VAR_REAL(rose_shear_x, 0.0),
    VAR_REAL(rose_shear_y, 0.0),
    VAR_REAL(rose_turn_x, 0.0),
    VAR_REAL(rose_turn_y, 0.0),
    VAR_REAL(rose_strength, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = sqrt(FTx * FTx + FTy * FTy);
    double t2 = atan2(FTx, FTy) + M_PI * VAR(rose_angle_in);
    double t3 = sin((VAR(rose_numer) / VAR(rose_denom)) * t2);
    double t4 = ((t1 * VAR(rose_outer_scale) - VAR(rose_outer_scale)) + 1.0) * VVAR;
    double t5 = (t3 * VAR(rose_strength) - VAR(rose_strength)) + 1.0;
    double t6 = t5 + VAR(rose_shear_x);
    double t7 = sin(VAR(rose_turn_x)) + cos(t2);
    double t8 = t4 * t6 * t7 + FPx;
    double t9 = t5 + VAR(rose_shear_y);
    double t10 = sin(VAR(rose_turn_y)) + sin(t2);
    double t11 = t4 * t9 * t10 + FPy;
    double t12 = ((t1 * VAR(rose_inner_scale) - VAR(rose_inner_scale)) + 1.0) * VVAR;
    double t13 = t12 * t6 * t7 + FPx;
    double t14 = t12 * t9 * t10 + FPy;
    int t15 = -(int)t3;
    int t16 = -(int)t1;
    if ((int)t1 < 0) {
        if ((int)t3 < 0) {
            if (t16 <= t15) {
                FPx = t13;
                FPy = t14;
            } else {
                FPx = t8;
                FPy = t11;
            }
        } else {
            if (t16 <= (int)t3) {
                FPx = t13;
                FPy = t14;
            } else {
                FPx = t8;
                FPy = t11;
            }
        }
    } else {
        if ((int)t3 < 0) {
            if ((int)t1 <= t15) {
                FPx = t13;
                FPy = t14;
            } else {
                FPx = t8;
                FPy = t11;
            }
        } else {
            if ((int)t1 <= (int)t3) {
                FPx = t13;
                FPy = t14;
            } else {
                FPx = t8;
                FPy = t11;
            }
        }
    }
    return TRUE;
}