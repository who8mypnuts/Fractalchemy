/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        julian_fl.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from julian_fl.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double julian_fl_power;
    double julian_fl_dist;
    double m_10;
    double m_18;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("julian_fl");
APO_VARIABLES(
    VAR_REAL(julian_fl_power, 2.0),
    VAR_REAL(julian_fl_dist, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    if (fabs(VAR(julian_fl_power)) >= 1.0) {
        VAR(m_18) = VAR(julian_fl_power);
        VAR(m_10) = 0.5 * ((1.0 / VAR(julian_fl_power)) * VAR(julian_fl_dist));
    } else {
        VAR(m_18) = VAR(julian_fl_power);
        VAR(m_10) = 0.5 * (VAR(julian_fl_power) * VAR(julian_fl_dist));
    }
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = M_2PI * (double)(int)trunc(random01() * (fabs(VAR(julian_fl_power)) - 1e-05)) + atan2(FTy, FTx);
    double t2 = (1.0 / VAR(m_18)) * t1;
    double t3 = pow(FTy * FTy + FTx * FTx, VAR(m_10)) * VVAR;
    double t4 = VAR(m_18) * t1;
    if (!(fabs(VAR(m_18)) > 1.0)) {
        FPx = cos(t4) * t3 + FPx;
        FPy = t3 * sin(t4) + FPy;
    } else {
        FPx = cos(t2) * t3 + FPx;
        FPy = t3 * sin(t2) + FPy;
    }
    return TRUE;
}