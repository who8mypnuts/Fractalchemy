/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        fibonacci2.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from fibonacci2.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double fibonacci2_sc;
    double fibonacci2_sc2;
    double m_0;
    double m_8;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("fibonacci2");
APO_VARIABLES(
    VAR_REAL(fibonacci2_sc, 1.0),
    VAR_REAL(fibonacci2_sc2, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_0) = 0.4472135954999579;
    VAR(m_8) = log(1.618033988749895);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTy * VAR(m_8);
    double t2 = VAR(m_8) * FTx;
    double t3 = exp(VAR(fibonacci2_sc2) * t2) * VAR(fibonacci2_sc);
    double t4 = -(M_PI * FTx + t1);
    double t5 = exp2(1545072828 * ((M_PI * FTy - t2) * VAR(fibonacci2_sc2))) * VAR(fibonacci2_sc);
    FPx = (cos(t1) * t3 - cos(t4) * t5) * VVAR * VAR(m_0) + FPx;
    FPy = (t3 * sin(t1) - t5 * sin(t4)) * VVAR * VAR(m_0) + FPy;
    return TRUE;
}