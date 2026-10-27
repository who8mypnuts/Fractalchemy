/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        rays3.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from rays3.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {

} Variables;
#include "apoplugin.h"
APO_PLUGIN("rays3");
APO_VARIABLES(

);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTy * FTy + FTx * FTx;
    double t2 = t1 * t1;
    double t3 = (VVAR / 10.0) * (1.0 / sqrt(cos(sin(1.0 / t2 + 1e-20) * sin(t2 + 1e-20))));
    FPx = cos(t1) * t3 * t1 / FTx;
    FPy = tan(t1) * t3 * t1 / FTy;
    return TRUE;
}