/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        uncube.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from uncube.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double uncube_cc;
    double uncube_pow;
    double m_10;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("uncube");
APO_VARIABLES(
    VAR_REAL(uncube_cc, 0.0),
    VAR_REAL(uncube_pow, 3.0)
);

int PluginVarPrepare(Variation* vp)
{
    if (VAR(uncube_pow) >= 0.0) {
        VAR(m_10) = VAR(uncube_pow);
    } else {
        VAR(m_10) = 0.02 * VAR(uncube_pow);
    }
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = pow(FTy * FTy + FTx * FTx, VAR(m_10));
    double t2 = sin(t1);
    double t3 = cos(t1);
    double t4 = pow(fabs(t3), VAR(m_10));
    double t5 = -t4;
    double t6 = cos(FTx);
    double t7 = 10.0 - VAR(uncube_cc);
    double t8 = 0.1 * ((0.4 * sin(3.5 * t5) + t6) * VAR(uncube_cc) + 1.4000000000000001 * (t5 * t6) * t7) * VVAR + FPx;
    double t9 = pow(fabs(t2), VAR(m_10));
    double t10 = -t9;
    double t11 = sin(FTx);
    double t12 = 0.1 * ((0.4 * cos(3.5 * t10) + t11) * VAR(uncube_cc) + t7 * (1.4000000000000001 * (t10 * t11))) * VVAR + FPy;
    double t13 = sin(27.0 * (FTy * (random01() * FTy * FTy))) * VVAR + FPz;
    double t14 = 0.1 * ((0.4 * sin(3.5 * t4) + t6) * VAR(uncube_cc) + 1.4000000000000001 * (t4 * t6) * t7) * VVAR + FPx;
    double t15 = 0.1 * ((0.4 * cos(3.5 * t9) + t11) * VAR(uncube_cc) + t7 * (1.4000000000000001 * (t9 * t11))) * VVAR + FPy;
    if (t2 > 0.0) {
        if (t3 > 0.0) {
            FPx = t14;
            FPy = t15;
            FPz = t13;
        } else {
            FPx = t8;
            FPy = t15;
            FPz = t13;
        }
    } else {
        if (t3 > 0.0) {
            FPx = t14;
            FPy = t12;
            FPz = t13;
        } else {
            FPx = t8;
            FPy = t12;
            FPz = t13;
        }
    }
    return TRUE;
}