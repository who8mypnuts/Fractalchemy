/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        pulse.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from pulse.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz', 32: 'TC'} var_base=88

typedef struct {
    double pulse_freqx;
    double pulse_freqy;
    double pulse_scalex;
    double pulse_scaley;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("pulse");
APO_VARIABLES(
    VAR_REAL(pulse_freqx, 2.0),
    VAR_REAL(pulse_freqy, 2.0),
    VAR_REAL(pulse_scalex, 1.0),
    VAR_REAL(pulse_scaley, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    FPx = (sin(VAR(pulse_freqx) * FTx) * VAR(pulse_scalex) + FTx) * VVAR + FPx;
    FPy = (sin(VAR(pulse_freqy) * FTy) * VAR(pulse_scaley) + FTy) * VVAR + FPy;
    return TRUE;
}