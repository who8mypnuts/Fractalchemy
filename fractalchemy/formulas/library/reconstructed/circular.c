/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        circular_x86.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from circular_x86.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double circular_angle;
    double circular_seed;
    double m_8;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("circular");
APO_VARIABLES(
    VAR_REAL(circular_angle, 4.45e-322),
    VAR_REAL(circular_seed, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_8) = 0.017453292519943295 * VAR(circular_angle);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = 43758.5453 * sin(78.233 * FTy + 12.9898 * FTx + VAR(circular_seed));
    double t2 = (VAR(m_8) + VAR(m_8)) * (random01() + (t1 + -1.0 - (double)(int)t1)) + atan2(FTy, FTx);
    double t3 = sqrt(FTx * FTx + FTy * FTy);
    FPx = cos(t2) * t3 * VVAR + FPx;
    FPy = t3 * sin(t2) * VVAR + FPy;
    return TRUE;
}