/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        ltube.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from ltube.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double ltube_n;
    double ltube_pi;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("ltube");
APO_VARIABLES(
    VAR_REAL(ltube_n, 3.0),
    VAR_REAL(ltube_pi, M_PI)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = VAR(ltube_pi) * FTy;
    double t2 = VAR(ltube_n) * t1;
    double t3 = FTx * VAR(ltube_pi);
    double t4 = t3 + t3;
    double t5 = 0.2 * sin(t4) + 2.0;
    FPx = sin(t2) * t5 * VVAR + FPx;
    FPy = (3.0 * cos(t1 + t1) + 0.2 * cos(t4)) * VVAR + FPy;
    FPz = t5 * cos(t2) * VVAR + FPz;
    return TRUE;
}