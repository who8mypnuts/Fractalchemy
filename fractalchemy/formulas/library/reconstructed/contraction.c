/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        contraction.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from contraction.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double contraction_edges;
    double m_0;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("contraction");
APO_VARIABLES(
    VAR_REAL_CYCLE(contraction_edges, -1.0, 1.0, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_0) = 0.1;
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = sqrt(FTy * FTy + FTx * FTx + 1e-20) * VAR(contraction_edges) + (VVAR / (VAR(m_0) + 1e-20));
    double t2 = VVAR / 10.0;
    FPx = FTx * t1 * t2 + FPx;
    FPy = FTy * t1 * t2 + FPy;
    return TRUE;
}