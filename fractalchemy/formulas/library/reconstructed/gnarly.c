/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        gnarly_x86.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from gnarly_x86.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double gnarly_cellsize;
    double gnarly_twist;
    double m_10;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("gnarly");
APO_VARIABLES(
    VAR_REAL(gnarly_cellsize, 1.0),
    VAR_REAL(gnarly_twist, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    double t1 = 0.5 * VAR(gnarly_cellsize);
    VAR(m_10) = t1 * t1;
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = (floor(FTx / VAR(gnarly_cellsize)) + 0.5) * VAR(gnarly_cellsize);
    double t2 = FTx - t1;
    double t3 = VAR(gnarly_cellsize) * (floor(FTy / VAR(gnarly_cellsize)) + 0.5);
    double t4 = FTy - t3;
    double t5 = t2 * t2 + t4 * t4;
    double t6 = log(t5 / VAR(m_10)) * VAR(gnarly_twist);
    double t7 = sin(t6);
    double t8 = cos(t6);
    double t9 = FPx + FTx * VVAR;
    double t10 = FPy + FTy * VVAR;
    if (VAR(gnarly_cellsize) == 0.0) {
        FPx = t9;
        FPy = t10;
    } else {
        if (t5 > VAR(m_10)) {
            FPx = t9;
            FPy = t10;
        } else {
            FPx = (t7 * t4 + t8 * t2 + t1) * VVAR + FPx;
            FPy = (t8 * t4 + t3 - t2 * t7) * VVAR + FPy;
        }
    }
    return TRUE;
}