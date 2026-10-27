/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        klein.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from klein.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double klein_pi;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("klein");
APO_VARIABLES(
    VAR_REAL(klein_pi, M_PI)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = cos(FTx);
    double t2 = 1.0 - (t1 / 2.0);
    double t3 = t2 + t2;
    double t4 = cos(FTy);
    double t5 = sin(FTx);
    double t6 = 3.0 * t1 * (t5 + 1.0);
    double t7 = VVAR * (t3 * t1 * t4 + t6) + FPx;
    double t8 = 8.0 * t5;
    double t9 = VVAR * (t3 * t5 * t4 + t8) + FPy;
    double t10 = VVAR * (t3 * sin(FTy)) + FPz;
    if (FTx > VAR(klein_pi)) {
        if (VAR(klein_pi) + VAR(klein_pi) >= FTx) {
            FPx = VVAR * (cos(FTy + M_PI) * t3 + t6) + FPx;
            FPy = VVAR * t8 + FPy;
            FPz = t10;
        } else {
            FPx = t7;
            FPy = t9;
            FPz = t10;
        }
    } else {
        FPx = t7;
        FPy = t9;
        FPz = t10;
    }
    return TRUE;
}