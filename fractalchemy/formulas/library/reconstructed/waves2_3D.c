/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        waves2_3D.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from waves2_3D.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double waves2_3D_freq;
    double waves2_3D_scale;
    double m_10;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("waves2_3D");
APO_VARIABLES(
    VAR_REAL(waves2_3D_freq, 2.0),
    VAR_REAL(waves2_3D_scale, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_10) = 0.5 * (FTy + FTx);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    FPx = (sin(VAR(waves2_3D_freq) * FTy) * VAR(waves2_3D_scale) + FTx) * VVAR + FPx;
    FPy = (sin(VAR(waves2_3D_freq) * FTx) * VAR(waves2_3D_scale) + FTy) * VVAR + FPy;
    FPz = (sin(VAR(waves2_3D_freq) * VAR(m_10)) * VAR(waves2_3D_scale) + FTz) * VVAR + FPz;
    return TRUE;
}