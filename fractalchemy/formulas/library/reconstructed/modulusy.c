/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        modulusy_x86.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from modulusy_x86.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double modulusy_y;
    double modulusy_shift;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("modulusy");
APO_VARIABLES(
    VAR_REAL(modulusy_y, 1.0),
    VAR_REAL(modulusy_shift, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = fmod(VAR(modulusy_shift) + VAR(modulusy_y) + FTy, VAR(modulusy_y) + VAR(modulusy_y));
    double t2 = FTx * VVAR + FPx;
    if (t1 < 0.0) {
        FPy = (t1 + VAR(modulusy_y)) * VVAR + FPy;
        FPx = t2;
    } else {
        FPy = (t1 - VAR(modulusy_y)) * VVAR + FPy;
        FPx = t2;
    }
    return TRUE;
}