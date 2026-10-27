/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        conic2.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from conic2.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double conic2_eccentricity;
    double conic2_holes;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("conic2");
APO_VARIABLES(
    VAR_REAL(conic2_eccentricity, 0.5),
    VAR_REAL(conic2_holes, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = atan2(FTy, FTx);
    double t2 = cos(t1);
    double t3 = (random01() - VAR(conic2_holes)) * (VAR(conic2_eccentricity) / (VAR(conic2_eccentricity) * t2 + 1.0));
    FPx = t2 * (VVAR * t3) + FPx;
    FPy = t3 * VVAR * sin(t1) + FPy;
    return TRUE;
}