/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        popcorn2_3D.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from popcorn2_3D.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double popcorn2_3D_x;
    double popcorn2_3D_y;
    double popcorn2_3D_z;
    double popcorn2_3D_c;
    double m_20;
    double m_28;
    double m_30;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("popcorn2_3D");
APO_VARIABLES(
    VAR_REAL(popcorn2_3D_x, 0.1),
    VAR_REAL(popcorn2_3D_y, 0.1),
    VAR_REAL(popcorn2_3D_z, 0.1),
    VAR_REAL(popcorn2_3D_c, 3.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_20) = atan2(FTy, FTz);
    VAR(m_28) = atan2(FTx, FTz);
    VAR(m_30) = atan2(sqrt(FTy * FTy + FTx * FTx), 1.0);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = 0.5 * ((sin(tan(FTy * VAR(popcorn2_3D_c))) * VAR(popcorn2_3D_x) + FTx) * VVAR) + FPx;
    double t2 = 0.5 * ((sin(tan(FTx * VAR(popcorn2_3D_c))) * VAR(popcorn2_3D_y) + FTy) * VVAR) + FPy;
    double t3 = sin(tan(VAR(popcorn2_3D_c)));
    double t4 = t3 * VAR(popcorn2_3D_z);
    double t5 = atan2(FTy, FTx);
    double t6 = fabs(VVAR) * VVAR;
    double t7 = t5 * (t3 * t6);
    double t8 = t4 * t7 * t6;
    double t9 = t4 * FTz;
    double t10 = t9 * t6;
    double t11 = t5 * (t3 * VVAR);
    double t12 = t4 * t11 * VVAR;
    double t13 = t9 * VVAR;
    if (VVAR > 1.0) {
        if (FPz != 0.0) {
            if (!(FTz != 0.0)) {
                FPx = t1;
                FPy = t2;
                FPz = t12 + FPz;
            } else {
                FPx = t1;
                FPy = t2;
                FPz = t13 + FPz;
            }
        } else {
            if (FTz != 0.0) {
                FPx = t1;
                FPy = t2;
                FPz = t13 + t11;
            } else {
                FPx = t1;
                FPy = t2;
                FPz = t12 + t11;
            }
        }
    } else {
        if (FPz != 0.0) {
            if (!(FTz != 0.0)) {
                FPx = t1;
                FPy = t2;
                FPz = t8 + FPz;
            } else {
                FPx = t1;
                FPy = t2;
                FPz = t10 + FPz;
            }
        } else {
            if (FTz != 0.0) {
                FPx = t1;
                FPy = t2;
                FPz = t10 + t7;
            } else {
                FPx = t1;
                FPy = t2;
                FPz = t8 + t7;
            }
        }
    }
    return TRUE;
}