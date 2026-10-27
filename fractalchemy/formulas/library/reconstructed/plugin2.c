/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        cloth3D.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from cloth3D.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {

} Variables;
#include "apoplugin.h"
APO_PLUGIN("plugin2");
APO_VARIABLES(

);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = sin(M_PI) * VVAR;
    double t2 = atan(FTx - FTy);
    double t3 = VVAR * FTx;
    double t4 = sin(t1);
    FPx = (cos(t1) * sin(t2) + t3) / 3.0 + FPx;
    FPy = (t4 + VVAR * FTy * t2) / 3.0 + FPy;
    FPz = (t4 + t3 * t2) / 3.0 + FPz;
    return TRUE;
}