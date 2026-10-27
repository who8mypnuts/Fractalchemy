/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        svf.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from svf.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double svf_n;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("svf");
APO_VARIABLES(
    VAR_REAL(svf_n, 2.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = cos(VAR(svf_n) * FTy);
    double t2 = cos(FTy);
    FPx = VVAR * (cos(FTx) * t1 * t2) + FPx;
    FPy = VVAR * (sin(FTx) * t1 * t2) + FPy;
    FPz = VVAR * (t1 * sin(FTy)) + FPz;
    return TRUE;
}