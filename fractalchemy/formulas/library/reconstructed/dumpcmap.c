/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        dumpcmap.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from dumpcmap.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz', 32: 'TC'} var_base=88

typedef struct {

} Variables;
#include "apoplugin.h"
APO_PLUGIN("dumpcmap");
APO_VARIABLES(

);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = random01();
    double t2 = (t1 + t1 - 1.0) * VVAR;
    double t3 = t2 + FPx;
    FPx = t3;
    FPy = t2 + FPy;
    FPz = VVAR * FTz + FPz;
    TC = fmod(fabs(0.5 * (t3 + 1.0)), 1.0);
    return TRUE;
}