/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        cannabiscurve_x86.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from cannabiscurve_x86.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    int cannabiscurve_filled;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("cannabiscurve");
APO_VARIABLES(
    VAR_INTEGER_NONZERO(cannabiscurve_filled, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = atan2(FTy, FTx);
    double t2 = t1 + M_PI_2;
    double t3 = sin(t2);
    double t4 = (sin(t1) + 1.0) * ((0.1 * cos(24.0 * t1) + 1.0) * (0.9 * cos(8.0 * t1) + 1.0)) * (0.1 * cos(200.0 * t1) + 0.9);
    double t5 = 3.725290312339702e-09 * t4 * (double)((rand() ^ rand() << 15) & 268435455);
    double t6 = cos(t2);
    double t7 = FTz * VVAR + FPz;
    if ((double)VAR(cannabiscurve_filled) <= 0.5) {
        FPx = t3 * t4 * VVAR + FPx;
        FPy = t4 * t6 * VVAR + FPy;
        FPz = t7;
    } else {
        FPx = t3 * t5 * VVAR + FPx;
        FPy = t5 * t6 * VVAR + FPy;
        FPz = t7;
    }
    return TRUE;
}