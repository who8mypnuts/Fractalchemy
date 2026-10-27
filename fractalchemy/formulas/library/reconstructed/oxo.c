/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        oxo.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from oxo.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double oxo_alkfdsef;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("oxo");
APO_VARIABLES(
    VAR_REAL_CYCLE(oxo_alkfdsef, -2.0, 2.0, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTy / (sqrt(FTx * FTx + FTy * FTy) + 1e-20);
    double t2 = sin(t1);
    double t3 = asin(t2 * VAR(oxo_alkfdsef));
    FPx = sin(t3) * (-FTx * t2) * VVAR + FPx;
    FPy = cos(t3) * (cos(t1) * -FTy) * VVAR + FPy;
    return TRUE;
}