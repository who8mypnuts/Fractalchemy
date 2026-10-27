/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        shift_x86.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from shift_x86.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double shift_x;
    double shift_y;
    double shift_angle;
    double m_18;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("shift");
APO_VARIABLES(
    VAR_REAL(shift_x, 0.0),
    VAR_REAL(shift_y, 0.0),
    VAR_REAL(shift_angle, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_18) = 0.017453292519943295 * VAR(shift_angle);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = cos(VAR(m_18));
    double t2 = sin(VAR(m_18));
    FPx = (t1 * VAR(shift_x) + FTx - VAR(shift_y) * t2) * VVAR + FPx;
    FPy = ((FTy - t1 * VAR(shift_y)) - t2 * VAR(shift_x)) * VVAR + FPy;
    return TRUE;
}