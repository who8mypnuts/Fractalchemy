/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        disc3d.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from disc3d.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double disc3d_pi;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("disc3d");
APO_VARIABLES(
    VAR_REAL(disc3d_pi, M_PI)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = atan2(FTx, FTy) * VVAR / (VAR(disc3d_pi) + 1e-20);
    double t2 = sqrt(FTy * FTy + FTx * FTx + 1e-20);
    double t3 = VAR(disc3d_pi) * t2;
    FPx = t1 * sin(t3) + FPx;
    FPy = t1 * cos(t3) + FPy;
    FPz = cos(FTz) * t2 * t1 + FPz;
    return TRUE;
}