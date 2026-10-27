/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        wings.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from wings.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double wings_reach;
    double wings_flap;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("wings");
APO_VARIABLES(
    VAR_REAL(wings_reach, 1.0),
    VAR_REAL(wings_flap, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = VAR(wings_flap) + FTy;
    double t2 = cosh(0.5 * (VAR(wings_reach) * FTy + (VAR(wings_reach) + FTy))) * sin(t1);
    double t3 = sqrt(cos(FTx) * t2);
    double t4 = VVAR / (sqrt(FTx * FTx + FTy * FTy) + 1e-20);
    double t5 = -t4;
    double t6 = t3 * t5 + FPx;
    double t7 = sqrt(fabs(t2 * sin(FTx)));
    double t8 = t5 * t7 + FPy;
    double t9 = t4 * cos(t1) + FPz;
    double t10 = t4 * t7 + FPy;
    double t11 = t3 * t4 + FPx;
    if (!(random01() > 0.5)) {
        if (!(random01() > 0.5)) {
            FPx = t11;
            FPy = t10;
            FPz = t9;
        } else {
            FPx = t11;
            FPy = t8;
            FPz = t9;
        }
    } else {
        if (!(random01() > 0.5)) {
            FPx = t6;
            FPy = t10;
            FPz = t9;
        } else {
            FPx = t6;
            FPy = t8;
            FPz = t9;
        }
    }
    return TRUE;
}