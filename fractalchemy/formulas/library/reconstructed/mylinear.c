/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        mylinear.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from mylinear.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    int mylinear_case;
    double mylinear_b;
    double mylinear_c;
    double m_0;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("mylinear");
APO_VARIABLES(
    VAR_INTEGER(mylinear_case, 6),
    VAR_REAL(mylinear_b, 0.0),
    VAR_REAL(mylinear_c, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = random01();
    double t2 = t1 * VAR(mylinear_c);
    double t3 = cos(VAR(mylinear_b) + FTy);
    double t4 = fabs(sin(t2)) + t3;
    double t5 = FTx * FTx + FTy * FTy;
    double t6 = cos(VAR(mylinear_b) / (FTy + 1e-20));
    double t7 = t2 + sin(FTx) * t6;
    double t8 = cos(FTy);
    double t9 = t2 + t8 * sin(VAR(mylinear_b) / (FTx + 1e-20));
    double t10 = t2 + t6;
    double t11 = t2 + t3;
    if (VAR(mylinear_case) > 6) {
        FPx = FTx * VAR(m_0) * VVAR + FPx;
        FPy = FTy * VAR(m_0) * VVAR + FPy;
        FPz = atan2(M_PI * VAR(m_0), t5) * VVAR + FPz;
    } else {
        if (VAR(mylinear_case) == 0) {
            VAR(m_0) = 1.0;
            FPx = FTx * VVAR + FPx;
            FPy = FTy * VVAR + FPy;
            FPz = atan2(M_PI, t5) * VVAR + FPz;
        } else if (VAR(mylinear_case) == 1) {
            VAR(m_0) = t1;
            FPx = FTx * t1 * VVAR + FPx;
            FPy = FTy * t1 * VVAR + FPy;
            FPz = atan2(M_PI * t1, t5) * VVAR + FPz;
        } else if (VAR(mylinear_case) == 2) {
            VAR(m_0) = t8;
            FPx = FTx * t8 * VVAR + FPx;
            FPy = FTy * t8 * VVAR + FPy;
            FPz = atan2(M_PI * t8, t5) * VVAR + FPz;
        } else if (VAR(mylinear_case) == 3) {
            VAR(m_0) = t11;
            FPx = FTx * t11 * VVAR + FPx;
            FPy = FTy * t11 * VVAR + FPy;
            FPz = atan2(M_PI * t11, t5) * VVAR + FPz;
        } else if (VAR(mylinear_case) == 4) {
            VAR(m_0) = t10;
            FPx = FTx * t10 * VVAR + FPx;
            FPy = FTy * t10 * VVAR + FPy;
            FPz = atan2(M_PI * t10, t5) * VVAR + FPz;
        } else if (VAR(mylinear_case) == 5) {
            if (FTy > FTx) {
                VAR(m_0) = t9;
                FPx = FTx * t9 * VVAR + FPx;
                FPy = FTy * t9 * VVAR + FPy;
                FPz = atan2(M_PI * t9, t5) * VVAR + FPz;
            } else {
                VAR(m_0) = t7;
                FPx = FTx * t7 * VVAR + FPx;
                FPy = FTy * t7 * VVAR + FPy;
                FPz = atan2(M_PI * t7, t5) * VVAR + FPz;
            }
        } else if (VAR(mylinear_case) == 6) {
            VAR(m_0) = t4;
            FPx = FTx * t4 * VVAR + FPx;
            FPy = FTy * t4 * VVAR + FPy;
            FPz = atan2(M_PI * t4, t5) * VVAR + FPz;
        }
    }
    return TRUE;
}