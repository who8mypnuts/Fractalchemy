/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        interference.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from interference.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double intrfr_a1;
    double intrfr_b1;
    double intrfr_c1;
    double intrfr_p1;
    double intrfr_a2;
    double intrfr_b2;
    double intrfr_c2;
    double intrfr_p2;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("interference");
APO_VARIABLES(
    VAR_REAL(intrfr_a1, 1.0),
    VAR_REAL(intrfr_b1, 1.0),
    VAR_REAL(intrfr_c1, 0.0),
    VAR_REAL(intrfr_p1, 1.0),
    VAR_REAL(intrfr_a2, 1.0),
    VAR_REAL(intrfr_b2, 1.0),
    VAR_REAL(intrfr_c2, 0.0),
    VAR_REAL(intrfr_p2, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    FPx = (pow(sin(FTx * VAR(intrfr_b2) + VAR(intrfr_c2)), VAR(intrfr_p2)) * VAR(intrfr_a2) + pow(sin(FTx * VAR(intrfr_b1) + VAR(intrfr_c1)), VAR(intrfr_p1)) * VAR(intrfr_a1)) * VVAR + FPx;
    FPy = (pow(sin(FTy * VAR(intrfr_b2) + VAR(intrfr_c2)), VAR(intrfr_p2)) * VAR(intrfr_a2) + pow(sin(FTy * VAR(intrfr_b1) + VAR(intrfr_c1)), VAR(intrfr_p1)) * VAR(intrfr_a1)) * VVAR + FPy;
    return TRUE;
}