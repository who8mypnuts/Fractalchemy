/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        spherivoid.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from spherivoid.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double spherivoid_radius;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("spherivoid");
APO_VARIABLES(
    VAR_REAL(spherivoid_radius, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = atan2(FTy, FTx);
    double t2 = hypot(FTz, hypot(FTy, FTx));
    double t3 = acos(FTz / t2);
    double t4 = sin(t3);
    double t5 = VAR(spherivoid_radius) + t2;
    FPx = VVAR * cos(t1) * t4 * t5 + FPx;
    FPy = VVAR * sin(t1) * t4 * t5 + FPy;
    FPz = VVAR * cos(t3) * t5 + FPz;
    return TRUE;
}