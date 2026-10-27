/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        post_julia3Dq.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from post_julia3Dq.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    int post_julia3Dq_power;
    int post_julia3Dq_divisor;
    double m_10;
    double m_18;
    double m_20;
    double m_8;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("post_julia3Dq");
APO_VARIABLES(
    VAR_INTEGER(post_julia3Dq_power, 3),
    VAR_INTEGER(post_julia3Dq_divisor, 2)
);

int PluginVarPrepare(Variation* vp)
{
    double t1 = 1.0 / (double)VAR(post_julia3Dq_power);
    double t2 = t1 * (double)VAR(post_julia3Dq_divisor);
    VAR(m_20) = M_2PI * t1;
    VAR(m_8) = t2;
    VAR(m_10) = fabs(t2);
    VAR(m_18) = 0.5 * t2 - 0.5;
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = VAR(m_10) * FPz;
    double t2 = FPy * FPy + FPx * FPx;
    double t3 = pow(t1 * t1 + t2, VAR(m_18)) * VVAR;
    double t4 = atan2(FPy, FPx) * VAR(m_8) + VAR(m_20) * (double)rand();
    double t5 = sqrt(t2) * t3;
    FPz = t3 * t1;
    FPx = cos(t4) * t5;
    FPy = t5 * sin(t4);
    return TRUE;
}