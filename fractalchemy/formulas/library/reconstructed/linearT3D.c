/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        linearT3D.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from linearT3D.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double lT3D_powX;
    double lT3D_powY;
    double lT3D_powZ;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("linearT3D");
APO_VARIABLES(
    VAR_REAL(lT3D_powX, 1.0),
    VAR_REAL(lT3D_powY, 1.0),
    VAR_REAL(lT3D_powZ, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = pow(fabs(FTx), VAR(lT3D_powX));
    double t2 = -t1 * VVAR + FPx;
    double t3 = pow(fabs(FTy), VAR(lT3D_powY));
    double t4 = -t3 * VVAR + FPy;
    double t5 = pow(fabs(FTz), VAR(lT3D_powZ));
    double t6 = -t5 * VVAR + FPz;
    double t7 = t5 * VVAR + FPz;
    double t8 = t3 * VVAR + FPy;
    double t9 = t1 * VVAR + FPx;
    if (FTx >= 0.0) {
        if (FTy >= 0.0) {
            if (FTz >= 0.0) {
                FPx = t9;
                FPy = t8;
                FPz = t7;
            } else {
                FPx = t9;
                FPy = t8;
                FPz = t6;
            }
        } else {
            if (FTz >= 0.0) {
                FPx = t9;
                FPy = t4;
                FPz = t7;
            } else {
                FPx = t9;
                FPy = t4;
                FPz = t6;
            }
        }
    } else {
        if (FTy >= 0.0) {
            if (FTz >= 0.0) {
                FPx = t2;
                FPy = t8;
                FPz = t7;
            } else {
                FPx = t2;
                FPy = t8;
                FPz = t6;
            }
        } else {
            if (FTz >= 0.0) {
                FPx = t2;
                FPy = t4;
                FPz = t7;
            } else {
                FPx = t2;
                FPy = t4;
                FPz = t6;
            }
        }
    }
    return TRUE;
}