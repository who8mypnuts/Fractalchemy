/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        pre_julia3Dz.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from pre_julia3Dz.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz', 32: 'TC'} var_base=88

typedef struct {
    int pre_julia3Dz_power;
    double m_10;
    double m_8;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("pre_julia3Dz");
APO_VARIABLES(
    VAR_INTEGER_NONZERO(pre_julia3Dz_power, 2)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_8) = fabs((double)VAR(pre_julia3Dz_power));
    VAR(m_10) = 0.5 * (1.0 / (double)VAR(pre_julia3Dz_power));
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTx * FTx + FTy * FTy;
    double t2 = sqrt(t1);
    double t3 = (M_2PI * (double)(rand() % (int)VAR(m_8)) + atan2(FTy, FTx)) / (double)(int)(double)VAR(pre_julia3Dz_power);
    double t4 = pow(t1, VAR(m_10)) * VVAR;
    double t5 = cos(t3) * t4;
    double t6 = sin(t3) * t4;
    double t7 = t4 * FTz;
    double t8 = t7 / (t2 * VAR(m_8));
    double t9 = sqrt(1e-20);
    double t10 = t7 / (t9 * VAR(m_8));
    if (t1 == 0.0) {
        FTx = t5;
        FTy = t6;
        FTz = t10;
    } else {
        FTx = t5;
        FTy = t6;
        FTz = t8;
    }
    return TRUE;
}