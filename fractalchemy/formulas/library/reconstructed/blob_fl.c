/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        blob_fl.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from blob_fl.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double blob_fl_low;
    double blob_fl_high;
    double blob_fl_waves;
    double m_18;
    double m_20;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("blob_fl");
APO_VARIABLES(
    VAR_REAL(blob_fl_low, 0.425),
    VAR_REAL(blob_fl_high, 1.0),
    VAR_REAL(blob_fl_waves, 4.0)
);

int PluginVarPrepare(Variation* vp)
{
    double t1 = 0.5 * ((VAR(blob_fl_high) - VAR(blob_fl_low)) * VVAR);
    VAR(m_18) = t1;
    VAR(m_20) = VAR(blob_fl_low) * VVAR + t1;
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = sin(atan2(FTx, FTy) * VAR(blob_fl_waves)) * VAR(m_18) + VAR(m_20);
    FPx = FTx * t1 + FPx;
    FPy = t1 * FTy + FPy;
    return TRUE;
}