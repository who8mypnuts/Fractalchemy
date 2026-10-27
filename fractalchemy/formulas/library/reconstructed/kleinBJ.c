/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        kleinBJ.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from kleinBJ.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double kleinBJ_necks;
    double kleinBJ_scale;
    double kleinBJ_spins;
    double kleinBJ_xblob;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("kleinBJ");
APO_VARIABLES(
    VAR_REAL(kleinBJ_necks, -3.0),
    VAR_REAL(kleinBJ_scale, 1.5),
    VAR_REAL(kleinBJ_spins, 0.5),
    VAR_REAL(kleinBJ_xblob, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = M_PI * (FTx * VAR(kleinBJ_xblob));
    double t2 = M_PI * (VAR(kleinBJ_necks) * FTx);
    double t3 = M_PI * ((VAR(kleinBJ_necks) + 1.0) * VAR(kleinBJ_spins) * FTx);
    double t4 = VAR(kleinBJ_necks) - 1.0;
    double t5 = sin(t4 * FTx) + VAR(kleinBJ_scale);
    double t6 = (1.0 / (VAR(kleinBJ_necks) + 1e-20)) * t4 * t5;
    double t7 = M_PI * FTy;
    double t8 = cos(t7);
    FPx = ((VAR(kleinBJ_necks) * cos(t1) - cos(t2)) - sin(t3) * t6 * t8) + FPx;
    FPy = t8 * (cos(t3) * t6) + (sin(t1) * VAR(kleinBJ_necks) - sin(t2)) + FPy;
    FPz = sin(t7) * t5 + FPz;
    return TRUE;
}