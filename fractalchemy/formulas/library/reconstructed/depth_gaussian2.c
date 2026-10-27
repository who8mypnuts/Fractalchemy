/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        depth_gaussian2_x86.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from depth_gaussian2_x86.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double dg2_blur;
    double dg2_radius;
    double dg2_x0;
    double dg2_y0;
    double dg2_mulx;
    double dg2_muly;
    double dg2_exp;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("depth_gaussian2");
APO_VARIABLES(
    VAR_REAL(dg2_blur, 1.0),
    VAR_REAL(dg2_radius, 1.0),
    VAR_REAL(dg2_x0, 0.0),
    VAR_REAL(dg2_y0, 0.0),
    VAR_REAL(dg2_mulx, 1.0),
    VAR_REAL(dg2_muly, 1.0),
    VAR_REAL(dg2_exp, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = (FTx - VAR(dg2_x0)) / VAR(dg2_mulx);
    double t2 = (FTy - VAR(dg2_y0)) / VAR(dg2_muly);
    double t3 = sqrt(t1 * t1 + t2 * t2);
    double t4 = exp(log(t3 - VAR(dg2_radius)) * VAR(dg2_exp)) * (0.1 * (sqrt(-2.0 * log(random01())) * VAR(dg2_blur)));
    double t5 = 2.3406689355471266e-08 * (double)((rand() ^ rand() << 15) & 268435455);
    if (t3 > VAR(dg2_radius)) {
        FPx = (t4 * cos(t5) + FTx) * VVAR + FPx;
        FPy = (sin(t5) * t4 + FTy) * VVAR + FPy;
    } else {
        FPx = FTx * VVAR + FPx;
        FPy = FTy * VVAR + FPy;
    }
    return TRUE;
}