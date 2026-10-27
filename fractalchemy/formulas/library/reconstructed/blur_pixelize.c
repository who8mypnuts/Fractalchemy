/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        blur_pixelizejf315.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from blur_pixelizejf315.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double blur_pixelize_size;
    double blur_pixelize_scale;
    double m_10;
    double m_18;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("blur_pixelize");
APO_VARIABLES(
    VAR_REAL(blur_pixelize_size, 0.1),
    VAR_REAL(blur_pixelize_scale, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_10) = 1.0 / VAR(blur_pixelize_size);
    VAR(m_18) = VVAR * VAR(blur_pixelize_size);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = (random01() - 0.5) * VAR(blur_pixelize_scale);
    FPx = (t1 + floor(FTx * VAR(m_10)) + 0.5) * VAR(m_18) + FPx;
    FPy = (t1 + floor(FTy * VAR(m_10)) + 0.5) * VAR(m_18) + FPy;
    return TRUE;
}