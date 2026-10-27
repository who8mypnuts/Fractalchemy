/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        Splits3D.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from Splits3D.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double splits3D_x;
    double splits3D_y;
    double splits3D_z;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("splits3D");
APO_VARIABLES(
    VAR_REAL(splits3D_x, 0.0),
    VAR_REAL(splits3D_y, 0.0),
    VAR_REAL(splits3D_z, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = (FTx - VAR(splits3D_x)) * VVAR + FPx;
    double t2 = (FTy - VAR(splits3D_y)) * VVAR + FPy;
    double t3 = (FTz - VAR(splits3D_z)) * VVAR + FPz;
    double t4 = (FTz + VAR(splits3D_z)) * VVAR + FPz;
    double t5 = (FTy + VAR(splits3D_y)) * VVAR + FPy;
    double t6 = (FTx + VAR(splits3D_x)) * VVAR + FPx;
    if (FTx >= 0.0) {
        if (FTy >= 0.0) {
            if (FTz >= 0.0) {
                FPx = t6;
                FPy = t5;
                FPz = t4;
            } else {
                FPx = t6;
                FPy = t5;
                FPz = t3;
            }
        } else {
            if (FTz >= 0.0) {
                FPx = t6;
                FPy = t2;
                FPz = t4;
            } else {
                FPx = t6;
                FPy = t2;
                FPz = t3;
            }
        }
    } else {
        if (FTy >= 0.0) {
            if (FTz >= 0.0) {
                FPx = t1;
                FPy = t5;
                FPz = t4;
            } else {
                FPx = t1;
                FPy = t5;
                FPz = t3;
            }
        } else {
            if (FTz >= 0.0) {
                FPx = t1;
                FPy = t2;
                FPz = t4;
            } else {
                FPx = t1;
                FPy = t2;
                FPz = t3;
            }
        }
    }
    return TRUE;
}