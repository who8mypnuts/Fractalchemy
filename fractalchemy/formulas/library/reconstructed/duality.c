/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        duality.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from duality.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double duality_pi;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("duality");
APO_VARIABLES(
    VAR_REAL(duality_pi, M_PI)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = VVAR / (FTx * FTx + FTy * FTy + 1e-20);
    double t2 = sin(FTx) * t1 + FPx;
    double t3 = cos(FTy) * t1 + FPy;
    double t4 = FTx * t1 + FPx;
    double t5 = FTy * t1 + FPy;
    if (FTx >= 0.0) {
        if (FTy >= 0.0) {
            FPx = -FTx * t1 + FPx;
            FPy = t5;
        } else {
            if (FTx > 0.0) {
                if (0.0 > FTy) {
                    FPx = t2;
                    FPy = t5;
                } else {
                    if (0.0 > FTx) {
                        if (FTy > 0.0) {
                            FPx = t4;
                            FPy = t3;
                        } else {
                            FPx = t2;
                            FPy = t3;
                        }
                    } else {
                        FPx = t2;
                        FPy = t3;
                    }
                }
            } else {
                if (0.0 > FTx) {
                    if (FTy > 0.0) {
                        FPx = t4;
                        FPy = t3;
                    } else {
                        FPx = t2;
                        FPy = t3;
                    }
                } else {
                    FPx = t2;
                    FPy = t3;
                }
            }
        }
    } else {
        if (FTx > 0.0) {
            if (0.0 > FTy) {
                FPx = t2;
                FPy = t5;
            } else {
                if (0.0 > FTx) {
                    if (FTy > 0.0) {
                        FPx = t4;
                        FPy = t3;
                    } else {
                        FPx = t2;
                        FPy = t3;
                    }
                } else {
                    FPx = t2;
                    FPy = t3;
                }
            }
        } else {
            if (0.0 > FTx) {
                if (FTy > 0.0) {
                    FPx = t4;
                    FPy = t3;
                } else {
                    FPx = t2;
                    FPy = t3;
                }
            } else {
                FPx = t2;
                FPy = t3;
            }
        }
    }
    return TRUE;
}