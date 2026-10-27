/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        depth_sine_x86.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from depth_sine_x86.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double ds_power;
    double ds_blur;
    double ds_radius;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("depth_sine");
APO_VARIABLES(
    VAR_REAL(ds_power, 1.0),
    VAR_REAL(ds_blur, 1.0),
    VAR_REAL(ds_radius, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    if (0.0 <= VAR(ds_power)) {
    } else {
        VAR(ds_power) = 0.0;
    }
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = sqrt(FTy * FTy + FTx * FTx);
    double t2 = exp(log(random01()) * VAR(ds_power));
    double t3 = (t1 - VAR(ds_radius)) * (0.1 * VAR(ds_blur));
    double t4 = M_1_PI * acos(t2 + t2 - 1.0) * t3;
    double t5 = 2.3406689355471266e-08 * (double)((rand() ^ rand() << 15) & 268435455);
    double t6 = cos(t5);
    double t7 = sin(t5);
    double t8 = M_1_PI * acos(7.450580624679404e-09 * (double)((rand() ^ rand() << 15) & 268435455) - 1.0) * t3;
    if (t1 > VAR(ds_radius)) {
        if (1.0 == VAR(ds_power)) {
            FPx = (t8 * t6 + FTx) * VVAR + FPx;
            FPy = (t7 * t8 + FTy) * VVAR + FPy;
        } else {
            FPx = (t4 * t6 + FTx) * VVAR + FPx;
            FPy = (t7 * t4 + FTy) * VVAR + FPy;
        }
    } else {
        FPx = FTx * VVAR + FPx;
        FPy = FTy * VVAR + FPy;
    }
    return TRUE;
}