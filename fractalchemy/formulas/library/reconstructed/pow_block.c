/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        powblock.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from powblock.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double pow_numerator;
    double pow_denominator;
    double pow_root;
    double pow_correctn;
    double pow_correctd;
    double m_28;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("pow_block");
APO_VARIABLES(
    VAR_REAL(pow_numerator, 3.0),
    VAR_REAL(pow_denominator, 2.0),
    VAR_REAL(pow_root, 1.0),
    VAR_REAL(pow_correctn, 1.0),
    VAR_REAL(pow_correctd, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_28) = VAR(pow_numerator) / (VAR(pow_correctn) * VAR(pow_denominator) / VAR(pow_correctd) + 1e-20);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = VAR(pow_denominator) + 1e-20;
    double t2 = (M_2PI * (floor(random01() * VAR(pow_denominator)) * VAR(pow_root)) * (1.0 / t1) + (atan2(FTy, FTx) / t1)) * VAR(pow_numerator);
    double t3 = pow(FTy * FTy + FTx * FTx, 0.5 * VAR(m_28)) * VVAR;
    FPx = cos(t2) * t3 + FPx;
    FPy = sin(t2) * t3 + FPy;
    return TRUE;
}