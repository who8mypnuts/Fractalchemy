/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        circular2_x86.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from circular2_x86.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double circular2_sigma;
    double m_8;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("circular2");
APO_VARIABLES(
    VAR_REAL(circular2_sigma, 4.45e-322)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_8) = 0.017453292519943295 * VAR(circular2_sigma);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = sqrt(-2.0 * log(random01())) * cos(2.3406689355471266e-08 * (double)((rand() ^ rand() << 15) & 268435455)) * VAR(m_8) + atan2(FTy, FTx);
    double t2 = sqrt(FTx * FTx + FTy * FTy);
    FPx = cos(t1) * t2 * VVAR + FPx;
    FPy = sin(t1) * t2 * VVAR + FPy;
    return TRUE;
}