/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        sphyp3D.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from sphyp3D.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double sphyp3D_stretchX;
    double sphyp3D_stretchY;
    double sphyp3D_stretchZ;
    int sphyp3D_zOn;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("sphyp3D");
APO_VARIABLES(
    VAR_REAL(sphyp3D_stretchX, 1.0),
    VAR_REAL(sphyp3D_stretchY, 1.0),
    VAR_REAL(sphyp3D_stretchZ, 1.0),
    VAR_INTEGER(sphyp3D_zOn, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTz * FTz + (FTy * FTy + FTx * FTx) + 1e-20;
    double t2 = FTx * (pow(t1, -VAR(sphyp3D_stretchX)) * VVAR) + FPx;
    double t3 = FTy * (pow(t1, -VAR(sphyp3D_stretchY)) * VVAR) + FPy;
    if (VAR(sphyp3D_zOn) != 1) {
        FPx = t2;
        FPy = t3;
    } else {
        FPx = t2;
        FPy = t3;
        FPz = FTz * (pow(t1, -VAR(sphyp3D_stretchZ)) * VVAR) + FPz;
    }
    return TRUE;
}