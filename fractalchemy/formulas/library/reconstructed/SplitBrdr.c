/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        Splitbrdr.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from Splitbrdr.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double splitb_x;
    double splitb_y;
    double splitb_px;
    double splitb_py;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("SplitBrdr");
APO_VARIABLES(
    VAR_REAL(splitb_x, 0.25),
    VAR_REAL(splitb_y, 0.25),
    VAR_REAL(splitb_px, 0.0),
    VAR_REAL(splitb_py, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = VVAR / (0.25 * (FTx * FTx + FTy * FTy) + 1.0);
    double t2 = FTx * t1 + FPx;
    double t3 = t1 * FTy + FPy;
    double t4 = rint(FTx);
    double t5 = FTx - t4;
    double t6 = 0.5 * t5 + t4;
    double t7 = t6 * VVAR + t2;
    double t8 = rint(FTy);
    double t9 = FTy - t8;
    double t10 = 0.5 * t9 + t8;
    double t11 = t10 * VVAR + t3;
    double t12 = VAR(splitb_px) * FTx;
    double t13 = VAR(splitb_py) * FTy;
    double t14 = (t6 - VAR(splitb_y)) * VVAR + t2;
    double t15 = t9 * VAR(splitb_y) / t5;
    double t16 = (t10 - t15) * VVAR + t3;
    double t17 = (t6 + VAR(splitb_x)) * VVAR + t2;
    double t18 = (t15 + t10) * VVAR + t3;
    double t19 = (t10 - VAR(splitb_y)) * VVAR + t3;
    double t20 = t5 / t9;
    double t21 = (t6 - t20 * VAR(splitb_x)) * VVAR + t2;
    double t22 = (t10 + VAR(splitb_y)) * VVAR + t3;
    double t23 = (t6 + t20 * VAR(splitb_y)) * VVAR + t2;
    if (random01() < 0.75) {
        if (fabs(t5) < fabs(t9)) {
            if (t9 >= 0.0) {
                FPx = t12 + t23;
                FPy = t13 + t22;
            } else {
                FPx = t12 + t21;
                FPy = t13 + t19;
            }
        } else {
            if (t5 >= 0.0) {
                FPx = t12 + t17;
                FPy = t13 + t18;
            } else {
                FPx = t12 + t14;
                FPy = t13 + t16;
            }
        }
    } else {
        FPx = t12 + t7;
        FPy = t13 + t11;
    }
    return TRUE;
}