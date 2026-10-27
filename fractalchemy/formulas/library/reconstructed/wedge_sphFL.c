/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        wedge_sphFL.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from wedge_sphFL.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double wedge_sphFL_angle;
    double wedge_sphFL_hole;
    double wedge_sphFL_count;
    double wedge_sphFL_swirl;
    double m_18;
    double m_20;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("wedge_sphFL");
APO_VARIABLES(
    VAR_REAL(wedge_sphFL_angle, M_PI_2),
    VAR_REAL(wedge_sphFL_hole, 0.0),
    VAR_REAL(wedge_sphFL_count, 2.0),
    VAR_REAL(wedge_sphFL_swirl, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_20) = 0.15915494309189535;
    VAR(m_18) = 1.0 - 0.15915494309189535 * (VAR(wedge_sphFL_count) * VAR(wedge_sphFL_angle));
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = 1.0 / sqrt(FTy * FTy + FTx * FTx + 1e-20);
    double t2 = VAR(wedge_sphFL_swirl) * t1 + atan2(FTy, FTx);
    double t3 = floor((VAR(wedge_sphFL_count) * t2 + M_PI) * VAR(m_20)) * VAR(wedge_sphFL_angle) + t2 * VAR(m_18);
    FPx = cos(t3) * ((VAR(wedge_sphFL_hole) + t1) * VVAR) + FPx;
    FPy = sin(t3) * ((t1 + VAR(wedge_sphFL_hole)) * VVAR) + FPy;
    return TRUE;
}