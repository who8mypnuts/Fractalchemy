/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        sschecks.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from sschecks.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double sschecks_x;
    double sschecks_y;
    double sschecks_size;
    double sschecks_rnd;
    double m_20;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("sschecks");
APO_VARIABLES(
    VAR_REAL(sschecks_x, 0.5),
    VAR_REAL(sschecks_y, 0.5),
    VAR_REAL(sschecks_size, 0.5),
    VAR_REAL(sschecks_rnd, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_20) = 1.0 / (VAR(sschecks_size) + 1e-300);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = VVAR / (FTy * FTy + FTx * FTx + 1e-300);
    double t2 = sin(FTx) * t1;
    double t3 = random01() * VAR(sschecks_rnd);
    double t4 = sin(FTy) * t1;
    if (((int)round(FTx * VAR(m_20)) + (int)round(FTy * VAR(m_20)) & 1) == 0) {
        FPx = (t2 + VAR(sschecks_x)) * VVAR + FPx;
        FPy = (t4 + (t3 + VAR(sschecks_y))) * VVAR + FPy;
    } else {
        FPx = (t2 + (t3 - VAR(sschecks_x))) * VVAR + FPx;
        FPy = (t4 - VAR(sschecks_y)) * VVAR + FPy;
    }
    return TRUE;
}