/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        post_rotate_z.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from post_rotate_z.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double m_0;
    double m_8;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("post_rotate_z");
APO_VARIABLES(

);

int PluginVarPrepare(Variation* vp)
{
    double t1 = M_PI_2 * VVAR;
    VAR(m_0) = sin(t1);
    VAR(m_8) = cos(t1);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    FPx = FPx * VAR(m_8) + FPy * VAR(m_0);
    FPy = VAR(m_8) * FPy - VAR(m_0) * FPx;
    return TRUE;
}