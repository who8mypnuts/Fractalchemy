/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        droste.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from droste.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double droste_r1;
    double droste_r2;
    double m_10;
    double m_18;
    double m_20;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("droste");
APO_VARIABLES(
    VAR_REAL(droste_r1, 0.5),
    VAR_REAL(droste_r2, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    double t1 = atan(log(VAR(droste_r2) / VAR(droste_r1)) / M_2PI);
    double t2 = cos(t1);
    VAR(m_10) = t1;
    VAR(m_18) = t2 * t2;
    VAR(m_20) = t2 * sin(t1);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = sqrt(FTy * FTy + FTx * FTx);
    double t2 = atan2(FTy, FTx);
    double t3 = log(t1) * VAR(m_20) + t2 * VAR(m_18);
    double t4 = exp(t2 * -VAR(m_20)) * (pow(t1, VAR(m_18)) * VVAR);
    FPx = cos(t3) * t4 + FPx;
    FPy = t4 * sin(t3) + FPy;
    return TRUE;
}