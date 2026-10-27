/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        blur_zoom_jf.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from blur_zoom_jf.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double blur_zoom_length;
    double blur_zoom_x;
    double blur_zoom_y;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("blur_zoom");
APO_VARIABLES(
    VAR_REAL(blur_zoom_length, 0.0),
    VAR_REAL(blur_zoom_x, 0.0),
    VAR_REAL(blur_zoom_y, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = random01() * VAR(blur_zoom_length) + 1.0;
    FPx = ((FTx - VAR(blur_zoom_x)) * t1 + VAR(blur_zoom_x)) * VVAR + FPx;
    FPy = ((FTy + VAR(blur_zoom_y)) * t1 - VAR(blur_zoom_y)) * VVAR + FPy;
    return TRUE;
}