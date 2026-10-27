/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        modulusx_x86.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from modulusx_x86.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double modulusx_x;
    double modulusx_shift;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("modulusx");
APO_VARIABLES(
    VAR_REAL(modulusx_x, 1.0),
    VAR_REAL(modulusx_shift, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = fmod(VAR(modulusx_shift) + VAR(modulusx_x) + FTx, VAR(modulusx_x) + VAR(modulusx_x));
    double t2 = FTy * VVAR + FPy;
    if (t1 < 0.0) {
        FPx = (t1 + VAR(modulusx_x)) * VVAR + FPx;
        FPy = t2;
    } else {
        FPx = (t1 - VAR(modulusx_x)) * VVAR + FPx;
        FPy = t2;
    }
    return TRUE;
}