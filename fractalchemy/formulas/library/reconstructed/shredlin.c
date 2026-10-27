/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        shredlin.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from shredlin.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    int shredlin_xdistance;
    double shredlin_xwidth;
    int shredlin_ydistance;
    double shredlin_ywidth;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("shredlin");
APO_VARIABLES(
    VAR_INTEGER(shredlin_xdistance, 0),
    VAR_REAL(shredlin_xwidth, 0.5),
    VAR_INTEGER(shredlin_ydistance, 0),
    VAR_REAL(shredlin_ywidth, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTx / VAR(shredlin_xdistance);
    double t2 = FTy / VAR(shredlin_ydistance);
    FPz = FTz * VVAR + FPz;
    FPx = VVAR * VAR(shredlin_xdistance) * ((t1 - (double)(int)t1) * VAR(shredlin_xwidth) + (double)(int)t1 + (0.5 - (double)(int)(int)(0.0 > FTx)) * (1.0 - VAR(shredlin_xwidth)));
    FPy = VVAR * VAR(shredlin_ydistance) * ((t2 - (double)(int)t2) * VAR(shredlin_ywidth) + (double)(int)t2 + (0.5 - (double)(int)(int)(0.0 > FTy)) * (1.0 - VAR(shredlin_ywidth)));
    return TRUE;
}