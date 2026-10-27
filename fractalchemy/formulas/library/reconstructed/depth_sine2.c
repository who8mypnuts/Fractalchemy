/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        depth_sine2_x86.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from depth_sine2_x86.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double ds2_power;
    double ds2_blur;
    double ds2_radius;
    double ds2_x0;
    double ds2_y0;
    double ds2_mulx;
    double ds2_muly;
    double ds2_exp;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("depth_sine2");
APO_VARIABLES(
    VAR_REAL(ds2_power, 1.0),
    VAR_REAL(ds2_blur, 1.0),
    VAR_REAL(ds2_radius, 1.0),
    VAR_REAL(ds2_x0, 0.0),
    VAR_REAL(ds2_y0, 0.0),
    VAR_REAL(ds2_mulx, 1.0),
    VAR_REAL(ds2_muly, 1.0),
    VAR_REAL(ds2_exp, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    if (0.0 <= VAR(ds2_power)) {
    } else {
        VAR(ds2_power) = 0.0;
    }
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = (FTx - VAR(ds2_x0)) / VAR(ds2_mulx);
    double t2 = (FTy - VAR(ds2_y0)) / VAR(ds2_muly);
    double t3 = sqrt(t1 * t1 + t2 * t2);
    double t4 = exp(log(t3 - VAR(ds2_radius)) * VAR(ds2_exp));
    double t5 = exp(log(random01()) * VAR(ds2_power));
    double t6 = t4 * (0.1 * (M_1_PI * acos(t5 + t5 - 1.0) * VAR(ds2_blur)));
    double t7 = 2.3406689355471266e-08 * (double)((rand() ^ rand() << 15) & 268435455);
    double t8 = cos(t7);
    double t9 = sin(t7);
    double t10 = t4 * (0.1 * (M_1_PI * acos(7.450580624679404e-09 * (double)((rand() ^ rand() << 15) & 268435455) - 1.0) * VAR(ds2_blur)));
    if (t3 > VAR(ds2_radius)) {
        if (1.0 == VAR(ds2_power)) {
            FPx = (t10 * t8 + FTx) * VVAR + FPx;
            FPy = (t9 * t10 + FTy) * VVAR + FPy;
        } else {
            FPx = (t6 * t8 + FTx) * VVAR + FPx;
            FPy = (t9 * t6 + FTy) * VVAR + FPy;
        }
    } else {
        FPx = FTx * VVAR + FPx;
        FPy = FTy * VVAR + FPy;
    }
    return TRUE;
}