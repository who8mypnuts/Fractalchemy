/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        julia3Dz_fl.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from julia3Dz_fl.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double julia3Dz_fl_power;
    double m_10;
    double m_8;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("julia3Dz_fl");
APO_VARIABLES(
    VAR_REAL(julia3Dz_fl_power, 2.0)
);

int PluginVarPrepare(Variation* vp)
{
    if (fabs(VAR(julia3Dz_fl_power)) >= 1.0) {
        VAR(m_10) = VAR(julia3Dz_fl_power);
        VAR(m_8) = 0.5 * (1.0 / VAR(julia3Dz_fl_power));
    } else {
        VAR(m_10) = VAR(julia3Dz_fl_power);
        VAR(m_8) = VAR(julia3Dz_fl_power) + VAR(julia3Dz_fl_power);
    }
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = fabs(VAR(m_10));
    double t2 = FTy * FTy + FTx * FTx + 1e-05;
    double t3 = pow(t2, VAR(m_8)) * VVAR;
    double t4 = t3 * FTz;
    double t5 = 1.0 / sqrt(t2);
    double t6 = M_2PI * (double)(int)trunc(random01() * (t1 - 1e-05)) + atan2(FTy, FTx);
    double t7 = t6 * (1.0 / VAR(m_10));
    double t8 = t6 * VAR(m_10);
    if (!(t1 > 1.0)) {
        FPz = t1 * t4 * t5 + FPz;
        FPx = cos(t8) * t3 + FPx;
        FPy = sin(t8) * t3 + FPy;
    } else {
        FPz = (1.0 / t1) * t4 * t5 + FPz;
        FPx = cos(t7) * t3 + FPx;
        FPy = sin(t7) * t3 + FPy;
    }
    return TRUE;
}