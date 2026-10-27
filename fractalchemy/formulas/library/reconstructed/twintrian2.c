/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        twintrian2.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from twintrian2.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double m_0;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("twintrian2");
APO_VARIABLES(

);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_0) = M_PI * VVAR;
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = random01() * (sqrt(FTy * FTy + FTx * FTx + 1e-20) * VVAR);
    double t2 = sin(t1);
    double t3 = FTx * VVAR * (cos(t1) + log10(t2 * t2 + 1e-20));
    FPx = FPx + t3;
    FPy = (t3 - FTx * VAR(m_0) * t2) + FPy;
    return TRUE;
}