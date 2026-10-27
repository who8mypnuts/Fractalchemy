/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        hyposphere.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from hyposphere.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double hyposphere_a;
    double hyposphere_b;
    double hyposphere_rr;
    double hyposphere_z1;
    double hyposphere_z2;
    double hyposphere_z3;
    double m_30;
    double m_38;
    double m_40;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("hyposphere");
APO_VARIABLES(
    VAR_REAL(hyposphere_a, 3.0),
    VAR_REAL(hyposphere_b, 2.0),
    VAR_REAL(hyposphere_rr, 0.0),
    VAR_REAL(hyposphere_z1, 1.0),
    VAR_REAL(hyposphere_z2, 0.0),
    VAR_REAL(hyposphere_z3, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_30) = VAR(hyposphere_a) / ((VAR(hyposphere_a) - (VAR(hyposphere_b) + VAR(hyposphere_b))) + 1e-20);
    VAR(m_38) = VAR(hyposphere_a) + 1e-20 - VAR(hyposphere_b);
    VAR(m_40) = (VAR(hyposphere_a) - VAR(hyposphere_b)) / (VAR(hyposphere_b) + 1e-20);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTy * FTy;
    double t2 = FTz * FTz;
    double t3 = atan2(t1, t2);
    double t4 = cos(FTy);
    double t5 = ((cos(t3) * VAR(m_38) - cos(VAR(m_40) * t3) * VAR(hyposphere_b)) * VAR(m_30) + t4) * cos(FTx);
    double t6 = FTx * FTx;
    double t7 = atan2(t6, t2);
    double t8 = ((sin(VAR(m_40) * t7) * VAR(hyposphere_b) + cos(t7) * VAR(m_38)) * VAR(m_30) + t4) * sin(FTx);
    double t9 = sin(FTy);
    double t10 = VAR(hyposphere_z1) * t9 + VAR(m_38) * t9 * VAR(hyposphere_z2) + (2.0 / ((t1 + t6) / 4.0 + 1.0) - 1.0) * t9 * VAR(hyposphere_z3);
    double t11 = t5 * t5 + t8 * t8 + t10 * t10 + 1e-20;
    double t12 = 10.0 - VAR(hyposphere_rr);
    FPx = (VAR(hyposphere_rr) * t5 / t11 + (t12 * t5 / 10.0)) * VVAR + FPx;
    FPy = (VAR(hyposphere_rr) * t8 / t11 + (t12 * t8 / 10.0)) * VVAR + FPy;
    FPz = (VAR(hyposphere_rr) * t10 / t11 + (t12 * t10 / 10.0)) * VVAR + FPz;
    return TRUE;
}