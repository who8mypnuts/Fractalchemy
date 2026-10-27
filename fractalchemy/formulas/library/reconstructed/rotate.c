/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        rotate_x86.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from rotate_x86.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double rotate_angle;
    double m_8;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("rotate");
APO_VARIABLES(
    VAR_REAL(rotate_angle, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_8) = 0.017453292519943295 * VAR(rotate_angle);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = cos(VAR(m_8));
    double t2 = sin(VAR(m_8));
    FPx = (t1 * FTx - FTy * t2) * VVAR + FPx;
    FPy = (t2 * FTx + t1 * FTy) * VVAR + FPy;
    return TRUE;
}