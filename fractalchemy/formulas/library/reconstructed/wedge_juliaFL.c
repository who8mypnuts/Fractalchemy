/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        wedge_juliaFL.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from wedge_juliaFL.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double wedge_juliaFL_angle;
    double wedge_juliaFL_count;
    double wedge_juliaFL_power;
    double wedge_juliaFL_dist;
    double m_10;
    double m_18;
    double m_30;
    double m_38;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("wedge_juliaFL");
APO_VARIABLES(
    VAR_REAL(wedge_juliaFL_angle, M_PI_2),
    VAR_REAL(wedge_juliaFL_count, 2.0),
    VAR_REAL(wedge_juliaFL_power, 2.0),
    VAR_REAL(wedge_juliaFL_dist, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    double t1 = 1.0 - 0.15915494309189535 * (VAR(wedge_juliaFL_count) * VAR(wedge_juliaFL_angle));
    if (fabs(VAR(wedge_juliaFL_power)) >= 1.0) {
        VAR(m_18) = 0.15915494309189535;
        VAR(m_10) = t1;
        VAR(m_38) = VAR(wedge_juliaFL_power);
        VAR(m_30) = 0.5 * ((1.0 / VAR(wedge_juliaFL_power)) * VAR(wedge_juliaFL_dist));
    } else {
        VAR(m_18) = 0.15915494309189535;
        VAR(m_10) = t1;
        VAR(m_38) = VAR(wedge_juliaFL_power);
        VAR(m_30) = 0.5 * (VAR(wedge_juliaFL_power) * VAR(wedge_juliaFL_dist));
    }
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = fabs(VAR(m_38));
    double t2 = M_2PI * (double)(int)trunc(random01() * (t1 - 1e-05)) + atan2(FTy, FTx);
    double t3 = t2 * (1.0 / VAR(m_38));
    double t4 = t3 * VAR(m_10) + VAR(wedge_juliaFL_angle) * (double)(int)floor((VAR(wedge_juliaFL_count) * t3 + M_PI) * VAR(m_18));
    double t5 = pow(FTy * FTy + FTx * FTx, VAR(m_30)) * VVAR;
    double t6 = t2 * VAR(m_38);
    double t7 = t6 * VAR(m_10) + VAR(wedge_juliaFL_angle) * (double)(int)floor((VAR(wedge_juliaFL_count) * t6 + M_PI) * VAR(m_18));
    if (!(t1 > 1.0)) {
        FPx = cos(t7) * t5 + FPx;
        FPy = sin(t7) * t5 + FPy;
    } else {
        FPx = cos(t4) * t5 + FPx;
        FPy = sin(t4) * t5 + FPy;
    }
    return TRUE;
}