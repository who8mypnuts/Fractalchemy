/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        flower3D.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from flower3D.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double flower3D_holes;
    double flower3D_petals;
    double flower3D_zpetals;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("flower3D");
APO_VARIABLES(
    VAR_REAL(flower3D_holes, 0.0),
    VAR_REAL(flower3D_petals, 4.0),
    VAR_REAL(flower3D_zpetals, 4.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = atan2(FTy, FTx);
    double t2 = (random01() - VAR(flower3D_holes)) * cos(t1 * VAR(flower3D_petals));
    double t3 = VVAR * t2;
    double t4 = atan2(FTz, FTx) * VAR(flower3D_zpetals);
    double t5 = cos(t4);
    double t6 = sin(t1);
    FPx = cos(t1) * t3 * t5 + FPx;
    FPy = t5 * (t3 * t6) + FPy;
    FPz = sin(t4) * (t6 * (t2 * VVAR)) + FPz;
    return TRUE;
}