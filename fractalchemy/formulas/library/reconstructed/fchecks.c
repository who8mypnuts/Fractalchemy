/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        fchecks.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from fchecks.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double fchecks_x;
    double fchecks_y;
    double fchecks_size;
    double fchecks_rnd;
    double m_20;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("fchecks");
APO_VARIABLES(
    VAR_REAL(fchecks_x, 0.5),
    VAR_REAL(fchecks_y, 0.5),
    VAR_REAL(fchecks_size, 0.5),
    VAR_REAL(fchecks_rnd, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_20) = 1.0 / (VAR(fchecks_size) + 1e-20);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = random01() * VAR(fchecks_rnd);
    double t2 = VVAR * FTz + FPz;
    if (((int)(round(FTy * VAR(m_20)) + round(FTx * VAR(m_20))) & 1) == 0) {
        FPx = (FTx + VAR(fchecks_x)) * VVAR + FPx;
        FPy = (FTy + (t1 + VAR(fchecks_y))) * VVAR + FPy;
        FPz = t2;
    } else {
        FPx = (FTx + (t1 - VAR(fchecks_x))) * VVAR + FPx;
        FPy = (FTy - VAR(fchecks_y)) * VVAR + FPy;
        FPz = t2;
    }
    return TRUE;
}