/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        hypersphere.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from hypersphere.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double hypersphere_r;
    double hypersphere_n;
    double hypersphere_p;
    double hypersphere_rr;
    double hypersphere_z1;
    double hypersphere_z2;
    double hypersphere_z3;
    double m_38;
    double m_40;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("hypersphere");
APO_VARIABLES(
    VAR_REAL(hypersphere_r, 1.5),
    VAR_REAL(hypersphere_n, 8.0),
    VAR_REAL(hypersphere_p, 1.0),
    VAR_REAL(hypersphere_rr, 0.0),
    VAR_REAL(hypersphere_z1, 1.0),
    VAR_REAL(hypersphere_z2, 0.0),
    VAR_REAL(hypersphere_z3, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_38) = VAR(hypersphere_p) / 10.0;
    VAR(m_40) = VAR(hypersphere_r) + 1e-20 - VAR(hypersphere_n);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = pow(cos(VAR(hypersphere_n) * FTx) + VAR(hypersphere_r), VAR(m_38));
    double t2 = cos(FTy);
    double t3 = sin(FTx) * t1 * t2;
    double t4 = cos(FTx) * t1 * t2;
    double t5 = sin(FTy);
    double t6 = VAR(hypersphere_z1) * t5 + VAR(m_40) * t5 * VAR(hypersphere_z2) + (2.0 / ((FTy * FTy + FTx * FTx) / 4.0 + 1.0) - 1.0) * t5 * VAR(hypersphere_z3);
    double t7 = t3 * t3 + t4 * t4 + t6 * t6 + 1e-20;
    double t8 = 10.0 - VAR(hypersphere_rr);
    FPx = (VAR(hypersphere_rr) * t3 / t7 + (t8 * t3 / 10.0)) * VVAR + FPx;
    FPy = (VAR(hypersphere_rr) * t4 / t7 + (t8 * t4 / 10.0)) * VVAR + FPy;
    FPz = (VAR(hypersphere_rr) * t6 / t7 + (t8 * t6 / 10.0)) * VVAR + FPz;
    return TRUE;
}