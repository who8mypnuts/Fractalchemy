/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        SPS.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from SPS.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    int SPS_case;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("SPS");
APO_VARIABLES(
    VAR_INTEGER(SPS_case, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = 1.5 * FTx;
    double t2 = 0.4 * cos(t1) + 1.0;
    double t3 = cos(FTx);
    double t4 = 2.0 * t3;
    double t5 = cos(FTy);
    double t6 = 0.5 * t5;
    double t7 = t2 * t4 + t6 * t3;
    double t8 = sin(FTy);
    double t9 = 0.4 * sin(t1) + 0.5 * t8;
    double t10 = sin(FTx);
    double t11 = 2.0 * t10;
    double t12 = t2 * t11 + t6 * t10;
    double t13 = t7 * t7 + t9 * t9 + t12 * t12;
    double t14 = FTy * t3;
    double t15 = t14 * t14;
    double t16 = FTy * t10;
    double t17 = t16 * t16;
    double t18 = 0.2 * FTx;
    double t19 = t15 + t17 + t18 * t18;
    double t20 = VVAR * FTx;
    double t21 = t20 + FPx;
    double t22 = VVAR * FTy;
    double t23 = t22 + FPy;
    double t24 = 0.0 * VVAR + FPz;
    double t25 = FTx * FTx;
    double t26 = FTy * FTy;
    double t27 = VVAR * (t25 - t26) + FPz;
    double t28 = t3 * t8;
    double t29 = VVAR * t28 + FPx;
    double t30 = t10 * t8;
    double t31 = VVAR * t30 + FPy;
    double t32 = log(tan(FTy / 2.0)) + t5;
    double t33 = VVAR * t26 + FPz;
    double t34 = t28 * t28;
    double t35 = t30 * t30;
    double t36 = t5 * t5;
    double t37 = t5 * t28;
    double t38 = t28 * t30;
    double t39 = t35 - t36;
    double t40 = t36 - t34;
    double t41 = t28 + t30 + t5;
    double t42 = pow(t5, 2.0);
    double t43 = FTx + FTx;
    double t44 = FTy + FTy;
    double t45 = sin(t44);
    double t46 = t3 / 2.0;
    double t47 = t3 * t5;
    double t48 = t10 * t5;
    double t49 = 2.0 * FTx;
    double t50 = 0.5 * FTx;
    double t51 = 0.75 * (M_SQRT2 * cos(3.0 * FTx + (M_PI / 0.0 /* uninitialised local */)));
    double t52 = VVAR * (cos(t49) + t4 - sin(t50) * t51 * t5) + FPx;
    double t53 = VVAR * ((t11 - sin(t49)) - cos(t50) * t51 * t5) + FPy;
    double t54 = VVAR * (FTz * t8) + FPz;
    double t55 = FTx / 2.0;
    double t56 = cos(t55);
    double t57 = sin(t55);
    double t58 = t56 * t8 + 2.0 - t45 * t57;
    double t59 = 1.0 - t46;
    double t60 = t59 + t59;
    double t61 = 3.0 * t3;
    double t62 = t61 * (t10 + 1.0);
    double t63 = VVAR * (t60 * t3 * t5 + t62) + FPx;
    double t64 = 8.0 * t10;
    double t65 = VVAR * (t60 * t10 * t5 + t64) + FPy;
    double t66 = VVAR * (t60 * t8) + FPz;
    double t67 = FTx / 3.0;
    double t68 = t67 + FTy;
    double t69 = cos(t68);
    double t70 = t67 - t44;
    double t71 = t69 + t69 + (cos(t70) + 7.0);
    double t72 = sin(t68);
    double t73 = t56 * FTy;
    double t74 = sin(0.0 /* uninitialised local */);
    double t75 = cosh(FTy) * t74;
    double t76 = cos(0.0 /* uninitialised local */);
    double t77 = sinh(FTy) * t76;
    double t78 = VVAR * (t3 * t75 + t10 * t77) + FPx;
    double t79 = VVAR * (t10 * t75 - t3 * t77) + FPy;
    double t80 = VVAR * (t74 * FTy + t76 * FTx) + FPz;
    double t81 = 1.25 * FTx;
    double t82 = 0.5 * cos(t81) + 1.0;
    double t83 = 0.3 * t5;
    double t84 = t5 + 3.0;
    double t85 = 7.0 * FTx;
    double t86 = t8 + 3.0;
    double t87 = VVAR * (t86 * t3) + FPx;
    double t88 = VVAR * (t86 * t10) + FPy;
    double t89 = VVAR * t5 + FPz;
    double t90 = VVAR * t8 + FPz;
    double t91 = cos(t43);
    double t92 = t91 * t10;
    double t93 = VVAR * t3;
    double t94 = t93 + FPz;
    double t95 = t25 + 1.0 + t26;
    double t96 = VVAR * t48;
    double t97 = (cos(5.0 * FTy) + 2.0) / 5.0;
    double t98 = t22 + FPz;
    double t99 = VVAR * t14 + FPx;
    double t100 = VVAR * t16 + FPy;
    if (VAR(SPS_case) > 44) {
        FPx = 0.0 /* uninitialised local */ * 0.0 /* uninitialised local */ + FPx;
        FPy = 0.0 /* uninitialised local */ * 0.0 /* uninitialised local */ + FPy;
        FPz = 0.0 /* uninitialised local */ * 0.0 /* uninitialised local */ + FPz;
    } else {
        if (VAR(SPS_case) == 0) {
            FPx = t21;
            FPy = t23;
            FPz = t24;
        } else if (VAR(SPS_case) == 1) {
            FPx = t21;
            FPy = t23;
            FPz = t27;
        } else if (VAR(SPS_case) == 2) {
            FPx = t21;
            FPy = t23;
            FPz = VVAR * cos(sqrt(t26 + t25 + 1e-20)) + FPz;
        } else if (VAR(SPS_case) == 3) {
            FPx = t93 + FPx;
            FPy = VVAR * t10 + FPy;
            FPz = t98;
        } else if (VAR(SPS_case) == 4) {
            FPx = t99;
            FPy = t100;
            FPz = t24;
        } else if (VAR(SPS_case) == 5) {
            FPx = t99;
            FPy = t100;
            FPz = t98;
        } else if (VAR(SPS_case) == 6) {
            FPx = t99;
            FPy = t100;
            FPz = VVAR * ((cos(t85) * FTy / 2.0) / 2.0) + FPz;
        } else if (VAR(SPS_case) == 7) {
            FPx = t99;
            FPy = t100;
            FPz = VVAR * (0.7 * FTx) + FPz;
        } else if (VAR(SPS_case) == 8) {
            FPx = t99;
            FPy = t100;
            FPz = t33;
        } else if (VAR(SPS_case) == 9) {
            FPx = t99;
            FPy = t100;
            FPz = t89;
        } else if (VAR(SPS_case) == 10) {
            FPx = t99;
            FPy = t100;
            FPz = VVAR * cos(-3.0 * FTx + FTy) + FPz;
        } else if (VAR(SPS_case) == 11) {
            FPx = VVAR * (t97 * t3) + FPx;
            FPy = VVAR * (t97 * t10) + FPy;
            FPz = t98;
        } else if (VAR(SPS_case) == 12) {
            FPx = t96 + FPx;
            FPy = t31;
            FPz = t94;
        } else if (VAR(SPS_case) == 13) {
            FPx = VVAR * t47 + FPx;
            FPy = t96 + FPy;
            FPz = t90;
        } else if (VAR(SPS_case) == 14) {
            FPx = VVAR * (t43 / t95) + FPx;
            FPy = VVAR * (t44 / t95) + FPy;
            FPz = VVAR * ((t25 + t26 - 1.0) / t95) + FPz;
        } else if (VAR(SPS_case) == 15) {
            FPx = VVAR * (t61 * t5) + FPx;
            FPy = VVAR * (3.0 * t10 * t5) + FPy;
            FPz = VVAR * (3.0 * t8 + 0.0 /* uninitialised local */ * FTx) + FPz;
        } else if (VAR(SPS_case) == 16) {
            FPx = VVAR * (t11 * t5) + FPx;
            FPy = t31;
            FPz = t94;
        } else if (VAR(SPS_case) == 17) {
            FPx = VVAR * (t92 * t5) + FPx;
            FPy = VVAR * (t92 * t8) + FPy;
            FPz = VVAR * (t91 * t3) + FPz;
        } else if (VAR(SPS_case) == 18) {
            FPx = VVAR * (t84 * t3) + FPx;
            FPy = VVAR * (t84 * t10) + FPy;
            FPz = t90;
        } else if (VAR(SPS_case) == 19) {
            FPx = t87;
            FPy = t88;
            FPz = t89;
        } else if (VAR(SPS_case) == 20) {
            FPx = t87;
            FPy = t88;
            FPz = VVAR * (t50 + t5) + FPz;
        } else if (VAR(SPS_case) == 21) {
            FPx = VVAR * (FTx * t3 * t84) + FPx;
            FPy = VVAR * (FTx * t10 * t84) + FPy;
            FPz = VVAR * (FTx * t8 - t85) + FPz;
        } else if (VAR(SPS_case) == 22) {
            FPx = VVAR * (t82 * t4 + t83 * t3) + FPx;
            FPy = VVAR * (2.5 * (0.5 * sin(t81) + 0.3 * t8)) + FPy;
            FPz = VVAR * (t82 * t11 + t83 * t10) + FPz;
        } else if (VAR(SPS_case) == 23) {
            FPx = VVAR * t7 + FPx;
            FPy = VVAR * t9 + FPy;
            FPz = VVAR * t12 + FPz;
        } else if (VAR(SPS_case) == 24) {
            FPx = t78;
            FPy = t79;
            FPz = t80;
        } else if (VAR(SPS_case) == 25) {
            FPx = t78;
            FPy = t79;
            FPz = t80;
        } else if (VAR(SPS_case) == 26) {
            FPx = t78;
            FPy = t79;
            FPz = t80;
        } else if (VAR(SPS_case) == 27) {
            FPx = VVAR * (t73 * t3 + t3) + FPx;
            FPy = VVAR * (t73 * t10 + t10) + FPy;
            FPz = VVAR * (t57 * FTy) + FPz;
        } else if (VAR(SPS_case) == 28) {
            FPx = VVAR * (t71 * t10) + FPx;
            FPy = VVAR * (t71 * t3) + FPy;
            FPz = VVAR * (t72 + t72 + sin(t70)) + FPz;
        } else if (VAR(SPS_case) == 29) {
            if (FTx > M_PI) {
                if (FTx >= M_2PI) {
                    FPx = VVAR * (cos(FTy + M_PI) * t60 + t62) + FPx;
                    FPy = VVAR * t64 + FPy;
                    FPz = t66;
                } else {
                    FPx = t63;
                    FPy = t65;
                    FPz = t66;
                }
            } else {
                FPx = t63;
                FPy = t65;
                FPz = t66;
            }
        } else if (VAR(SPS_case) == 30) {
            FPx = VVAR * (t58 * t3) + FPx;
            FPy = VVAR * (t58 * t10) + FPy;
            FPz = VVAR * (t45 * t56 + t57 * t8) + FPz;
        } else if (VAR(SPS_case) == 31) {
            FPx = t52;
            FPy = t53;
            FPz = t54;
        } else if (VAR(SPS_case) == 32) {
            FPx = t52;
            FPy = t53;
            FPz = t54;
        } else if (VAR(SPS_case) == 33) {
            FPx = VVAR * pow(t47, 3.0) + FPx;
            FPy = VVAR * pow(t48, 3.0) + FPy;
            FPz = VVAR * pow(t8, 3.0) + FPz;
        } else if (VAR(SPS_case) == 34) {
            FPx = VVAR * (t45 * t46) + FPx;
            FPy = VVAR * (t45 * (t10 / 2.0)) + FPy;
            FPz = VVAR * -(t42 - pow(t8, 2.0) * pow(t3, 2.0)) + FPz;
        } else if (VAR(SPS_case) == 35) {
            FPx = VVAR * (t42 * sin(t43)) + FPx;
            FPy = VVAR * (t45 * t10) + FPy;
            FPz = VVAR * (t45 * t3) + FPz;
        } else if (VAR(SPS_case) == 36) {
            FPx = VVAR * (0.5 * (((t34 + t34 - t35) - t36) + (t30 + t30) * t5 * (t35 - t34) + t37 * (t34 - t35) + t38 * t39)) + FPx;
            FPy = VVAR * (0.8660254037844386 * (t39 + t37 * t40 + t38 * t40)) + FPy;
            FPz = VVAR * ((pow(t41, 3.0) + 4.0 * (t30 - t28) * (t5 - t30) * (t28 - t5)) * t41) + FPz;
        } else if (VAR(SPS_case) == 37) {
            FPx = VVAR * (FTx * FTy) + FPx;
            FPy = t20 + FPy;
            FPz = t33;
        } else if (VAR(SPS_case) == 38) {
            FPx = t29;
            FPy = t31;
            FPz = VVAR * t32 + FPz;
        } else if (VAR(SPS_case) == 39) {
            FPx = t29;
            FPy = t31;
            FPz = VVAR * (t32 + t18) + FPz;
        } else if (VAR(SPS_case) == 40) {
            FPx = VVAR * ((FTx - (t25 * FTx / 3.0)) + t26 * FTx) + FPx;
            FPy = VVAR * ((FTy - (t26 * FTy / 3.0)) + t25 * FTy) + FPy;
            FPz = t27;
        } else if (VAR(SPS_case) == 41) {
            FPx = VVAR * ((t14 - (t15 * t14 / 3.0)) + t17 * t14) + FPx;
            FPy = VVAR * ((t16 - (t17 * t16 / 3.0)) + t15 * t16) + FPy;
            FPz = VVAR * (t15 - t17) + FPz;
        } else if (VAR(SPS_case) == 42) {
            FPx = t21;
            FPy = t23;
            FPz = t24;
        } else if (VAR(SPS_case) == 43) {
            FPx = VVAR * (t14 / t19) + FPx;
            FPy = VVAR * (t16 / t19) + FPy;
            FPz = VVAR * (t18 / t19) + FPz;
        } else if (VAR(SPS_case) == 44) {
            FPx = VVAR * (t7 / t13) + FPx;
            FPy = VVAR * (t9 / t13) + FPy;
            FPz = VVAR * (t12 / t13) + FPz;
        }
    }
    return TRUE;
}