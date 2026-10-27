/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        split_rotbeta_x86.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from split_rotbeta_x86.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double split_rot_sp;
    double split_rot_angle;
    double m_10;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("split_rot");
APO_VARIABLES(
    VAR_REAL(split_rot_sp, 0.0),
    VAR_REAL(split_rot_angle, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_10) = 0.017453292519943295 * VAR(split_rot_angle);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = cos(VAR(m_10));
    double t2 = t1 * FTx;
    double t3 = sin(VAR(m_10));
    double t4 = t3 * FTy;
    if (0.0 > FTx) {
        FPx = (t4 + t2 - VAR(split_rot_sp)) * VVAR + FPx;
        FPy = (t1 * FTy - t3 * FTx) * VVAR + FPy;
    } else {
        FPx = (t2 + VAR(split_rot_sp) - t4) * VVAR + FPx;
        FPy = (FTx * t3 + FTy * t1) * VVAR + FPy;
    }
    return TRUE;
}