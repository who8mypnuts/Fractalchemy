/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        petal3D.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from petal3D.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double petal3D_width;
    double petal3D_Zshape;
    double petal3D_scale1;
    double petal3D_scale2;
    double petal3D_style;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("petal3D");
APO_VARIABLES(
    VAR_REAL(petal3D_width, 1.0),
    VAR_REAL(petal3D_Zshape, 0.25),
    VAR_REAL(petal3D_scale1, 0.25),
    VAR_REAL(petal3D_scale2, 0.25),
    VAR_REAL(petal3D_style, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = cos(FTx);
    double t2 = cos(FTy);
    double t3 = t1 * t2;
    double t4 = t3 * t3 * t3 * (VVAR * t1) + FPx;
    double t5 = t2 * sin(FTx);
    double t6 = t5 * (t5 * t5) * (t1 * VVAR) * VAR(petal3D_width);
    double t7 = FPy + t6;
    double t8 = fabs(VAR(petal3D_scale1));
    double t9 = sin(fabs(M_PI * (VAR(petal3D_scale2) * FTy)));
    double t10 = sin(-M_PI * (VAR(petal3D_scale1) * FTx));
    double t11 = 0.5 * (t10 + FTx * (t8 - 1.0));
    double t12 = t9 + t11;
    double t13 = 0.5 * (t6 * VAR(petal3D_scale2));
    double t14 = t11 + t13;
    double t15 = copysign(0, VAR(petal3D_style));
    double t16 = 0.5 - VAR(petal3D_style) * VAR(petal3D_style);
    double t17 = t12 * t16;
    double t18 = t17 + t17;
    double t19 = 1.0 - (t16 + t16);
    double t20 = t14 * t19;
    double t21 = (0.0/0.0) * VVAR * VAR(petal3D_Zshape) + FPz;
    double t22 = 0.5 * t10;
    double t23 = t9 + t22;
    double t24 = t22 + t13;
    double t25 = t23 * t16;
    double t26 = t25 + t25;
    double t27 = t24 * t19;
    if (!(t8 > 1.0)) {
        if (VAR(petal3D_style) != 0.0) {
            if (!(fabs(VAR(petal3D_style)) > M_SQRT1_2)) {
                if (!(VAR(petal3D_style) >= 0.0)) {
                    FPx = t4;
                    FPy = t7;
                    FPz = (t26 - t27) * VVAR * VAR(petal3D_Zshape) + FPz;
                } else {
                    if (!(VAR(petal3D_style) > 0.0)) {
                        FPx = t4;
                        FPy = t7;
                        FPz = t21;
                    } else {
                        FPx = t4;
                        FPy = t7;
                        FPz = (t26 + t27) * VVAR * VAR(petal3D_Zshape) + FPz;
                    }
                }
            } else {
                FPx = t4;
                FPy = t7;
                FPz = t24 * t15 * VVAR * VAR(petal3D_Zshape) + FPz;
            }
        } else {
            FPx = t4;
            FPy = t7;
            FPz = t23 * VVAR * VAR(petal3D_Zshape) + FPz;
        }
    } else {
        if (VAR(petal3D_style) != 0.0) {
            if (!(fabs(VAR(petal3D_style)) > M_SQRT1_2)) {
                if (!(VAR(petal3D_style) >= 0.0)) {
                    FPx = t4;
                    FPy = t7;
                    FPz = (t18 - t20) * VVAR * VAR(petal3D_Zshape) + FPz;
                } else {
                    if (!(VAR(petal3D_style) > 0.0)) {
                        FPx = t4;
                        FPy = t7;
                        FPz = t21;
                    } else {
                        FPx = t4;
                        FPy = t7;
                        FPz = (t18 + t20) * VVAR * VAR(petal3D_Zshape) + FPz;
                    }
                }
            } else {
                FPx = t4;
                FPy = t7;
                FPz = t14 * t15 * VVAR * VAR(petal3D_Zshape) + FPz;
            }
        } else {
            FPx = t4;
            FPy = t7;
            FPz = t12 * VVAR * VAR(petal3D_Zshape) + FPz;
        }
    }
    return TRUE;
}