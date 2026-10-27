/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        wedge_fl.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from wedge_fl.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double wedge_fl_angle;
    double wedge_fl_hole;
    double wedge_fl_count;
    double wedge_fl_swirl;
    double m_18;
    double m_20;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("wedge_fl");
APO_VARIABLES(
    VAR_REAL(wedge_fl_angle, M_PI_2),
    VAR_REAL(wedge_fl_hole, 0.0),
    VAR_REAL(wedge_fl_count, 2.0),
    VAR_REAL(wedge_fl_swirl, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_20) = 0.15915494309189535;
    VAR(m_18) = 1.0 - 0.15915494309189535 * (VAR(wedge_fl_count) * VAR(wedge_fl_angle));
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = sqrt(FTy * FTy + FTx * FTx);
    double t2 = VAR(wedge_fl_swirl) * t1 + atan2(FTy, FTx);
    double t3 = t2 * VAR(m_18) + VAR(wedge_fl_angle) * (double)(int)floor((VAR(wedge_fl_count) * t2 + M_PI) * VAR(m_20));
    double t4 = (t1 + VAR(wedge_fl_hole)) * VVAR;
    FPx = cos(t3) * t4 + FPx;
    FPy = t4 * sin(t3) + FPy;
    return TRUE;
}