/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        sininv.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from sininv.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double sininv_x;
    double sininv_y;
    double sininv_xfreq;
    double sininv_yfreq;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("sininv");
APO_VARIABLES(
    VAR_REAL(sininv_x, 1.0),
    VAR_REAL(sininv_y, 1.0),
    VAR_REAL(sininv_xfreq, 1.0),
    VAR_REAL(sininv_yfreq, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    FPx = (cos(1.0 / (VAR(sininv_xfreq) * FTx)) * VAR(sininv_x) + FTx) * VVAR + FPx;
    FPy = (cos(1.0 / (VAR(sininv_yfreq) * FTy)) * VAR(sininv_y) + FTy) * VVAR + FPy;
    return TRUE;
}