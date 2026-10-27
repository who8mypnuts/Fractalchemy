/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        Projective.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from Projective.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double pr_A;
    double pr_B;
    double pr_C;
    double pr_A1;
    double pr_B1;
    double pr_C1;
    double pr_A2;
    double pr_B2;
    double pr_C2;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("projective");
APO_VARIABLES(
    VAR_REAL(pr_A, 0.0),
    VAR_REAL(pr_B, 0.0),
    VAR_REAL(pr_C, 1.0),
    VAR_REAL(pr_A1, 1.0),
    VAR_REAL(pr_B1, 0.0),
    VAR_REAL(pr_C1, 0.0),
    VAR_REAL(pr_A2, 0.0),
    VAR_REAL(pr_B2, 1.0),
    VAR_REAL(pr_C2, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = VAR(pr_A) * FTx + VAR(pr_B) * FTy + VAR(pr_C);
    FPx = (VAR(pr_A1) * FTx + VAR(pr_B1) * FTy + VAR(pr_C1)) * VVAR / t1 + FPx;
    FPy = (VAR(pr_A2) * FTx + VAR(pr_B2) * FTy + VAR(pr_C2)) * VVAR / t1 + FPy;
    return TRUE;
}